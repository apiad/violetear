---
title: "@app.shared — Realtime Cross-Client State Sync"
date: 2026-07-18
status: approved
target_version: v1.4
---

# @app.shared — Realtime Cross-Client State Sync

## 1. Problem

Building a collaborative feature today requires manual wiring:
- Declare Python-side state (`messages: list`, `users: dict`)
- Write `@app.server.realtime` handlers to mutate it
- Call `await fn.broadcast(...)` in every handler that changes state
- Write `@app.client.realtime` handlers to receive updates and mutate the DOM
- Write a `request_history` / `receive_history` pair for late-joiner sync
- Wire `@app.client.on("connect")` to trigger the history request

Example 05 (chat room) is ~180 lines of which roughly 100 are this boilerplate. `@app.shared` eliminates it.

## 2. Design decisions

| Decision | Choice | Rationale |
|---|---|---|
| Who can mutate? | Client-writable by default | Natural for collaborative UIs; server-only is opt-in per field |
| Conflict model | Last-write-wins, field-level replacement | Sufficient for v1; `SharedList` etc. land as separate types later |
| Late-joiner push | Automatic on connect | Zero boilerplate; lazy fields deferred |
| Client callbacks on shared fields | Deferred | `ReactiveRegistry.subscribe` already exists; add sugar later |
| Compiler enforcement of `server_only` | Deferred to v2 | Filed as follow-up in issue #11 |

## 3. Python API

```python
from dataclasses import dataclass, field
from violetear import App

app = App(title="Chat Room")

@app.shared
@dataclass
class Room:
    messages: list = field(default_factory=list)
    users: dict    = field(default_factory=dict)
    count: int     = 0
    # server_only=True in metadata → clients can read, cannot write
    version: str   = field(default="1.0", metadata={"server_only": True})
```

`@app.shared` wraps the decorated dataclass in a `SharedProxy` singleton,
registers it in `App.shared_registry`, and **returns the proxy** so the class
name in user code refers to the proxy (not the raw dataclass). The class name
is the stable identifier used on the wire and in the bundle.

**Server-side usage** (inside `@app.server.realtime`, lifecycle handlers, etc.):

```python
Room.count += 1                              # auto-broadcasts shared_sync
Room.users = {**Room.users, cid: "alice"}   # replaces field, broadcasts
Room.messages = Room.messages + [msg]        # replaces list, broadcasts
```

**Client-side usage** (inside `@app.client.callback`, etc.):

```python
async def on_click(event: Event):
    Room.count += 1   # sends shared_set → server validates → rebroadcasts
```

`server_only` fields: server can write freely; client `shared_set` is rejected
with a `shared_error` frame. Transpiler enforcement (compile-time error) is a
v2 follow-up (issue #11).

## 4. Server-side implementation

### 4.1 SharedProxy

```python
class SharedProxy:
    """Wraps a @dataclass instance; intercepts __setattr__ → broadcast."""

    def __init__(self, instance, registry: "SharedRegistry"):
        object.__setattr__(self, "_instance", instance)
        object.__setattr__(self, "_registry", registry)

    def __getattr__(self, name):
        return getattr(self._instance, name)

    def __setattr__(self, name, value):
        instance = object.__getattribute__(self, "_instance")
        registry = object.__getattribute__(self, "_registry")
        # Check server_only on the target field
        fields_meta = {f.name: f.metadata for f in dataclasses.fields(instance)}
        if name in fields_meta and fields_meta[name].get("server_only"):
            # Server can always write its own fields
            pass
        setattr(instance, name, value)
        asyncio.get_running_loop().create_task(
            registry.broadcast_sync(type(instance).__name__, name, value)
        )
```

### 4.2 SharedRegistry

Lives on `App`. Owns all shared state, the broadcast, and the late-joiner push.

```python
class SharedRegistry:
    def __init__(self, app: "App"):
        self._app = app
        self._classes: dict[str, SharedProxy] = {}  # cls_name → proxy
        self._meta: dict[str, dict] = {}            # cls_name → {field: metadata}

    def register(self, cls: type) -> SharedProxy:
        instance = cls()
        proxy = SharedProxy(instance, self)
        self._classes[cls.__name__] = proxy
        self._meta[cls.__name__] = {
            f.name: dict(f.metadata) for f in dataclasses.fields(instance)
        }
        return proxy

    async def broadcast_sync(self, cls_name: str, field: str, value):
        await self._app.socket_manager.broadcast_shared_sync(cls_name, field, value)

    async def push_to_new_client(self, client_id: str):
        """Called by SocketManager on connect — push all shared state."""
        for cls_name, proxy in self._classes.items():
            instance = object.__getattribute__(proxy, "_instance")
            for f in dataclasses.fields(instance):
                value = getattr(instance, f.name)
                await self._app.socket_manager.send_shared_sync(
                    client_id, cls_name, f.name, value
                )

    async def handle_set(self, client_id: str, cls_name: str, field: str, value):
        """Handle inbound shared_set from a client."""
        proxy = self._classes.get(cls_name)
        if proxy is None:
            return  # unknown class, ignore
        meta = self._meta.get(cls_name, {}).get(field, {})
        if meta.get("server_only"):
            await self._app.socket_manager.send_shared_error(
                client_id, cls_name, field, "server_only"
            )
            return
        # Type-validate value against field annotation (reuse existing validate.py).
        # On type mismatch, send shared_error with reason "type_error" and return.
        # Apply directly to instance (bypasses SharedProxy to avoid double-broadcast).
        setattr(object.__getattribute__(proxy, "_instance"), field, value)
        await self.broadcast_sync(cls_name, field, value)
```

### 4.3 SocketManager changes

Three new methods added to `SocketManager`:

- `broadcast_shared_sync(cls, field, value)` — sends `shared_sync` to all connections
- `send_shared_sync(client_id, cls, field, value)` — sends to one client
- `send_shared_error(client_id, cls, field, reason)` — sends error frame to one client

`connect()` calls `await self.app.shared_registry.push_to_new_client(client_id)`
after accepting the socket.

The WS dispatcher adds two new branches:
```python
elif data["type"] == "shared_set":
    await self.app.shared_registry.handle_set(
        client_id, data["class"], data["field"], data["value"]
    )
```

## 5. Wire protocol

All messages use the existing JSON WS envelope.

**Client → Server** (`shared_set`):
```json
{"type": "shared_set", "class": "Room", "field": "count", "value": 42}
```
Server validates class, field, not `server_only`, type check. On success:
updates instance, broadcasts `shared_sync` to **all** clients (including sender —
server value is the source of truth). On failure: sends `shared_error`.

**Server → Client** (`shared_sync`):
```json
{"type": "shared_sync", "class": "Room", "field": "count", "value": 42}
```
Client runtime sets the reactive field locally. ReactiveRegistry notifies
bound DOM elements. No echo back to server.

**Server → Client** (`shared_error`):
```json
{"type": "shared_error", "class": "Room", "field": "version", "reason": "server_only"}
```
Client receives this and (for now) logs to console. User-facing error handling
is a future concern.

**On connect**: server sends one `shared_sync` per field per registered
`@app.shared` class before yielding to the application's `on("connect")` handler.

## 6. Client-side: transpiler + runtime.js

### 6.1 Transpiler: new shared class template

`transpile_class` gains a `shared=True` mode. The emitted class differs in two
ways from a `@app.local` class:

1. Setters send `shared_set` upstream (unless `_shared._receiving` is set).
2. `server_only` fields have the `shared_set` call stripped — they receive
   updates but cannot send.

```javascript
// @app.shared RoomState — emitted by transpile_class(cls, shared=True)
class _Room {
  constructor() {
    this._count = 0;
    this._messages = [];
    this._users = {};
    this._version = "1.0";
  }
  get count() { return this._count; }
  set count(v) {
    (_checkInt)(v, "Room.count");
    this._count = v;
    ReactiveRegistry.notify("Room.count", v);
    if (!_shared._receiving) { _shared.set("Room", "count", v); }
  }
  // server_only field — no shared_set call
  get version() { return this._version; }
  set version(v) {
    (_checkStr)(v, "Room.version");
    this._version = v;
    ReactiveRegistry.notify("Room.version", v);
    // no _shared.set — server_only
  }
  // ... other fields
}
const Room = new _Room();
```

### 6.2 runtime.js: _shared object

A new `_shared` object (~30 lines) added to `runtime.js`:

```javascript
const _shared = {
  _receiving: false,

  set(cls, field, value) {
    // Sends shared_set over the existing WS connection
    _ws_send({type: "shared_set", class: cls, field: field, value: value});
  },

  handle(msg) {
    // Called by WS dispatcher when msg.type === "shared_sync"
    const obj = _shared_objects[msg.class];
    if (!obj) return;
    _shared._receiving = true;
    try { obj[msg.field] = msg.value; }
    finally { _shared._receiving = false; }
  },

  handle_error(msg) {
    console.error(`[shared] ${msg.class}.${msg.field} rejected: ${msg.reason}`);
  }
};

// Registry of shared class singletons (populated at bundle-gen time)
const _shared_objects = { Room: Room, /* ... */ };
```

The existing WS dispatcher in `runtime.js` gains two new cases:
```javascript
case "shared_sync":  _shared.handle(msg);       break;
case "shared_error": _shared.handle_error(msg); break;
```

`_ws_send` is a new helper that queues messages if the socket is not yet open
(guards against race between constructor and connect).

## 7. Bundle generation

`App._generate_bundle()` adds shared classes to the JS bundle after local classes:

```python
for cls_name, proxy in self.shared_registry._classes.items():
    instance = object.__getattribute__(proxy, "_instance")
    bundle += transpile_class(type(instance), shared=True) + "\n"
```

The `_shared_objects` map is emitted as a literal:
```python
entries = ", ".join(f'"{k}": {k}' for k in self.shared_registry._classes)
bundle += f"const _shared_objects = {{{entries}}};\n"
```

## 8. Revised example 05 (chat room)

The manual realtime wiring collapses to:

```python
@app.shared
@dataclass
class Room:
    messages: list = field(default_factory=list)
    users: dict    = field(default_factory=dict)

@app.server.on("connect")
async def on_join(client_id: str):
    Room.users = {**Room.users, client_id: f"anon-{client_id[:6]}"}
    Room.messages = Room.messages + [{"from": "system", "text": "... joined"}]

@app.server.on("disconnect")
async def on_leave(client_id: str):
    name = Room.users.pop(client_id, None)  # NOTE: mutates dict in place
    # For v1, reassign to trigger broadcast:
    users = dict(Room.users)
    users.pop(client_id, None)
    Room.users = users
    Room.messages = Room.messages + [{"from": "system", "text": f"{name} left"}]

@app.server.realtime
async def post_message(client_id: str, text: str):
    name = Room.users.get(client_id, "unknown")
    Room.messages = Room.messages + [{"from": name, "text": text.strip()}]
```

DOM updates in the view bind directly to `Room.messages` and `Room.users`.
The four `@app.client.realtime` handlers, `request_history`, `receive_history`,
and `@app.client.on("connect")` are **deleted**. A new example file
`examples/06_shared.py` will be the canonical demo for this feature.

## 9. Testing

- `tests/test_shared.py` — unit tests for `SharedProxy.__setattr__` interception,
  `SharedRegistry.handle_set` (including `server_only` rejection), late-joiner push
- `tests/test_transpile.py` — shared class template emission, `server_only` setter stripping
- `tests/test_examples.py` — example 06 renders without error
- Manual: two browser tabs on example 06, verify mutations in one tab propagate to the other

## 10. Out of scope for this version

- Persistence (Redis, SQLite) — in-memory only
- `SharedList`, `SharedDict` with semantic merge — deferred (issue placeholder)
- Compiler enforcement of `server_only` (transpile-time `ClientCompileError`) — issue #11
- Client-side callbacks on shared field changes — `ReactiveRegistry.subscribe` is already
  the hook; sugar API deferred
- Optimistic updates — client shows change immediately, rolls back on rejection
- Delta sync (send only changed fields across all `@app.shared` classes on connect)
