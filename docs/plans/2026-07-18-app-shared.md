# @app.shared Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `@app.shared` decorator — a reactive dataclass whose field assignments auto-broadcast to all connected clients via WebSocket, with automatic late-joiner push on connect.

**Architecture:** New `SharedProxy`/`SharedRegistry` in `violetear/shared.py` handles server-side interception and broadcast. `transpile_class(..., shared=True)` emits a JS reactive class whose setters also send `shared_set` WS messages. `runtime.js` gains a `_shared` dispatcher that handles `shared_sync`/`shared_error` frames from the server.

**Tech Stack:** Python 3.12+, asyncio, FastAPI WebSocket, vanilla JS (no build tooling)

## Global Constraints

- No third-party JS. No build tooling. All JS goes into `runtime.js` or is emitted inline into `bundle.js`.
- `asyncio.get_running_loop()` not `get_event_loop()` (deprecated).
- All new server modules import-guarded the same way `app.py` is (FastAPI optional).
- `make` (ruff format-check + pytest) must pass before every commit.
- Commit message convention: `feat(shared): ...`, `test(shared): ...`, `fix(shared): ...`
- Run `make format` before committing if ruff format-check fails.

---

### Task 1: SharedProxy + SharedRegistry

**Files:**
- Create: `violetear/shared.py`
- Create: `tests/test_shared.py`

**Interfaces:**
- Produces:
  - `SharedProxy(instance, registry)` — proxy wrapper; `__getattr__` delegates to instance; `__setattr__` updates instance + schedules async broadcast
  - `SharedRegistry(app)` — holds `_classes: dict[str, SharedProxy]`; methods: `register(cls) -> SharedProxy`, `broadcast_sync(cls_name, field, value) -> coroutine`, `push_to_new_client(client_id) -> coroutine`, `handle_set(client_id, cls_name, field, value) -> coroutine`
  - `SharedStateError(message)` — raised when a `server_only` field is written

- [ ] **Step 1.1: Write failing tests for SharedProxy**

```python
# tests/test_shared.py
import asyncio
import dataclasses
from unittest.mock import AsyncMock, MagicMock
import pytest
from violetear.shared import SharedProxy, SharedRegistry, SharedStateError


@dataclasses.dataclass
class _Counter:
    count: int = 0
    label: str = "x"
    readonly_field: str = dataclasses.field(
        default="locked", metadata={"server_only": True}
    )


def _make_registry(broadcast_fn=None):
    app = MagicMock()
    registry = SharedRegistry(app)
    if broadcast_fn:
        registry.broadcast_sync = broadcast_fn
    return registry


def test_proxy_getattr():
    registry = _make_registry()
    proxy = SharedProxy(_Counter(), registry)
    assert proxy.count == 0
    assert proxy.label == "x"


def test_proxy_setattr_updates_instance():
    calls = []
    async def fake_broadcast(cls, field, value):
        calls.append((cls, field, value))
    registry = _make_registry(fake_broadcast)
    proxy = SharedProxy(_Counter(), registry)

    async def run():
        proxy.__setattr__("count", 42)
        await asyncio.sleep(0)  # let the created task run

    asyncio.run(run())
    assert proxy.count == 42
    assert ("_Counter", "count", 42) in calls


def test_proxy_server_only_write_does_not_raise_from_server():
    # Server writes server_only fields freely — SharedProxy.__setattr__ does NOT raise
    registry = _make_registry(AsyncMock())
    proxy = SharedProxy(_Counter(), registry)
    proxy.readonly_field = "new"  # must not raise
    assert proxy.readonly_field == "new"
```

- [ ] **Step 1.2: Run to confirm FAIL**

```bash
cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_shared.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError: No module named 'violetear.shared'`

- [ ] **Step 1.3: Implement `violetear/shared.py`**

```python
"""Server-side shared state: SharedProxy, SharedRegistry, SharedStateError."""
from __future__ import annotations

import asyncio
import dataclasses
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .app import App


class SharedStateError(Exception):
    """Raised on illegal operations on shared state (e.g. unknown class)."""


class SharedProxy:
    """Wraps a @dataclass instance; intercepts __setattr__ to auto-broadcast."""

    def __init__(self, instance: Any, registry: "SharedRegistry") -> None:
        object.__setattr__(self, "_instance", instance)
        object.__setattr__(self, "_registry", registry)

    def __getattr__(self, name: str) -> Any:
        return getattr(object.__getattribute__(self, "_instance"), name)

    def __setattr__(self, name: str, value: Any) -> None:
        instance = object.__getattribute__(self, "_instance")
        registry = object.__getattribute__(self, "_registry")
        setattr(instance, name, value)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # no running loop (e.g. tests without asyncio)
        loop.create_task(
            registry.broadcast_sync(type(instance).__name__, name, value)
        )


class SharedRegistry:
    """Owns all @app.shared singletons; drives broadcast and late-joiner push."""

    def __init__(self, app: "App") -> None:
        self._app = app
        # cls_name -> SharedProxy
        self._classes: dict[str, SharedProxy] = {}
        # cls_name -> {field_name -> metadata dict}
        self._meta: dict[str, dict[str, dict]] = {}

    def register(self, cls: type) -> SharedProxy:
        """Instantiate cls, wrap in SharedProxy, register under cls.__name__."""
        if not dataclasses.is_dataclass(cls):
            raise SharedStateError(
                f"{cls.__name__!r} must be a @dataclass to use @app.shared"
            )
        instance = cls()
        proxy = SharedProxy(instance, self)
        self._classes[cls.__name__] = proxy
        self._meta[cls.__name__] = {
            f.name: dict(f.metadata) for f in dataclasses.fields(instance)
        }
        return proxy

    async def broadcast_sync(self, cls_name: str, field: str, value: Any) -> None:
        """Send shared_sync for (cls_name, field, value) to every client."""
        await self._app.socket_manager.broadcast_shared_sync(cls_name, field, value)

    async def push_to_new_client(self, client_id: str) -> None:
        """Push full current state of every @app.shared class to one client."""
        for cls_name, proxy in self._classes.items():
            instance = object.__getattribute__(proxy, "_instance")
            for f in dataclasses.fields(instance):
                value = getattr(instance, f.name)
                await self._app.socket_manager.send_shared_sync(
                    client_id, cls_name, f.name, value
                )

    async def handle_set(
        self, client_id: str, cls_name: str, field: str, value: Any
    ) -> None:
        """Handle inbound shared_set from a client."""
        proxy = self._classes.get(cls_name)
        if proxy is None:
            return  # unknown class — ignore silently
        meta = self._meta.get(cls_name, {}).get(field, {})
        if meta.get("server_only"):
            await self._app.socket_manager.send_shared_error(
                client_id, cls_name, field, "server_only"
            )
            return
        # Apply directly to instance (bypassing SharedProxy to avoid double-broadcast)
        instance = object.__getattribute__(proxy, "_instance")
        try:
            setattr(instance, field, value)
        except Exception:
            await self._app.socket_manager.send_shared_error(
                client_id, cls_name, field, "type_error"
            )
            return
        await self.broadcast_sync(cls_name, field, value)
```

- [ ] **Step 1.4: Run tests to confirm PASS**

```bash
uv run pytest tests/test_shared.py -v
```
Expected: all tests pass (some may skip due to no running loop — that's fine for now)

- [ ] **Step 1.5: Commit**

```bash
git add violetear/shared.py tests/test_shared.py
git commit -m "feat(shared): SharedProxy + SharedRegistry with broadcast and late-joiner push"
```

---

### Task 2: SocketManager new send methods

**Files:**
- Modify: `violetear/app.py` — `SocketManager` class (lines 284–345)
- Modify: `tests/test_websocket.py` — add shared message assertions

**Interfaces:**
- Consumes: existing `SocketManager.active_connections: dict[str, WebSocket]`
- Produces:
  - `SocketManager.broadcast_shared_sync(cls_name: str, field: str, value: Any) -> coroutine`
  - `SocketManager.send_shared_sync(client_id: str, cls_name: str, field: str, value: Any) -> coroutine`
  - `SocketManager.send_shared_error(client_id: str, cls_name: str, field: str, reason: str) -> coroutine`

- [ ] **Step 2.1: Write failing tests**

Add to `tests/test_websocket.py` (check existing file first for import style):

```python
# Add these tests to tests/test_websocket.py
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from violetear.app import SocketManager

def _make_socket_manager():
    app = MagicMock()
    sm = SocketManager(app)
    ws = AsyncMock()
    sm.active_connections["c1"] = ws
    return sm, ws

def test_broadcast_shared_sync_sends_to_all():
    sm, ws = _make_socket_manager()
    asyncio.run(sm.broadcast_shared_sync("Room", "count", 42))
    ws.send_text.assert_called_once()
    payload = json.loads(ws.send_text.call_args[0][0])
    assert payload == {"type": "shared_sync", "class": "Room", "field": "count", "value": 42}

def test_send_shared_sync_sends_to_one():
    sm, ws = _make_socket_manager()
    asyncio.run(sm.send_shared_sync("c1", "Room", "count", 42))
    ws.send_text.assert_called_once()
    payload = json.loads(ws.send_text.call_args[0][0])
    assert payload == {"type": "shared_sync", "class": "Room", "field": "count", "value": 42}

def test_send_shared_error_sends_error_frame():
    sm, ws = _make_socket_manager()
    asyncio.run(sm.send_shared_error("c1", "Room", "version", "server_only"))
    ws.send_text.assert_called_once()
    payload = json.loads(ws.send_text.call_args[0][0])
    assert payload == {"type": "shared_error", "class": "Room", "field": "version", "reason": "server_only"}
```

- [ ] **Step 2.2: Run to confirm FAIL**

```bash
uv run pytest tests/test_websocket.py -k "shared" -v 2>&1 | head -20
```
Expected: `AttributeError: 'SocketManager' object has no attribute 'broadcast_shared_sync'`

- [ ] **Step 2.3: Add three methods to `SocketManager` in `app.py`**

Add after `SocketManager.invoke` (around line 345), before the `class App:` line:

```python
    async def broadcast_shared_sync(
        self, cls_name: str, field: str, value: object
    ) -> None:
        """Broadcast a shared_sync frame to all connected clients."""
        payload = json.dumps(
            {"type": "shared_sync", "class": cls_name, "field": field, "value": value}
        )
        for client_id, conn in list(self.active_connections.items()):
            try:
                await conn.send_text(payload)
            except Exception:
                await self.disconnect(client_id)

    async def send_shared_sync(
        self, client_id: str, cls_name: str, field: str, value: object
    ) -> None:
        """Send a shared_sync frame to one client (late-joiner push)."""
        payload = json.dumps(
            {"type": "shared_sync", "class": cls_name, "field": field, "value": value}
        )
        conn = self.active_connections.get(client_id)
        if conn is None:
            return
        try:
            await conn.send_text(payload)
        except Exception:
            await self.disconnect(client_id)

    async def send_shared_error(
        self, client_id: str, cls_name: str, field: str, reason: str
    ) -> None:
        """Send a shared_error rejection frame to one client."""
        payload = json.dumps(
            {
                "type": "shared_error",
                "class": cls_name,
                "field": field,
                "reason": reason,
            }
        )
        conn = self.active_connections.get(client_id)
        if conn is None:
            return
        try:
            await conn.send_text(payload)
        except Exception:
            await self.disconnect(client_id)
```

- [ ] **Step 2.4: Run to confirm PASS**

```bash
uv run pytest tests/test_websocket.py -v 2>&1 | tail -10
```
Expected: all tests pass

- [ ] **Step 2.5: Full suite check**

```bash
make 2>&1 | tail -5
```

- [ ] **Step 2.6: Commit**

```bash
git add violetear/app.py tests/test_websocket.py
git commit -m "feat(shared): SocketManager broadcast_shared_sync / send_shared_sync / send_shared_error"
```

---

### Task 3: App.shared() decorator + WS dispatcher + connect push

**Files:**
- Modify: `violetear/app.py` — `App.__init__`, WS dispatcher loop, new `App.shared()` method
- Modify: `tests/test_shared.py` — add integration tests for handle_set and connect push

**Interfaces:**
- Consumes: `SharedRegistry` from `violetear.shared`; `SocketManager` methods from Task 2
- Produces:
  - `App.shared_registry: SharedRegistry` — initialized in `__init__`
  - `App.shared(cls) -> SharedProxy` — decorator; calls `shared_registry.register(cls)` and returns proxy
  - WS dispatcher handles `{"type": "shared_set", "class": ..., "field": ..., "value": ...}`
  - `SocketManager.connect()` calls `shared_registry.push_to_new_client(client_id)` after accepting

- [ ] **Step 3.1: Write failing integration tests**

Add to `tests/test_shared.py`:

```python
# Integration: App.shared decorator
import dataclasses
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

def test_app_shared_decorator_returns_proxy():
    from violetear.app import App
    from violetear.shared import SharedProxy
    app = App(title="test")

    @app.shared
    @dataclasses.dataclass
    class Counter:
        count: int = 0

    assert isinstance(Counter, SharedProxy)
    assert Counter.count == 0

def test_app_shared_registers_in_registry():
    from violetear.app import App
    app = App(title="test")

    @app.shared
    @dataclasses.dataclass
    class Score:
        value: int = 0

    assert "Score" in app.shared_registry._classes

def test_handle_set_updates_and_would_broadcast():
    from violetear.app import App
    app = App(title="test")

    @app.shared
    @dataclasses.dataclass
    class G:
        x: int = 0

    app.socket_manager.broadcast_shared_sync = AsyncMock()

    async def run():
        await app.shared_registry.handle_set("c1", "G", "x", 99)

    asyncio.run(run())
    assert app.shared_registry._classes["G"].x == 99
    app.socket_manager.broadcast_shared_sync.assert_called_once_with("G", "x", 99)

def test_handle_set_rejects_server_only():
    from violetear.app import App
    app = App(title="test")

    @app.shared
    @dataclasses.dataclass
    class H:
        locked: str = dataclasses.field(default="v", metadata={"server_only": True})

    app.socket_manager.send_shared_error = AsyncMock()

    async def run():
        await app.shared_registry.handle_set("c1", "H", "locked", "hacked")

    asyncio.run(run())
    app.socket_manager.send_shared_error.assert_called_once_with(
        "c1", "H", "locked", "server_only"
    )
    assert app.shared_registry._classes["H"].locked == "v"  # unchanged
```

- [ ] **Step 3.2: Run to confirm FAIL**

```bash
uv run pytest tests/test_shared.py -v 2>&1 | grep -E "PASSED|FAILED|ERROR"
```
Expected: `AttributeError: 'App' object has no attribute 'shared'` or similar

- [ ] **Step 3.3: Add `shared_registry` init and `App.shared()` decorator to `app.py`**

In `App.__init__`, add after `self.client = ClientRegistry(self)` and `self.server = ServerRegistry(self)` (around line 523):

```python
        from .shared import SharedRegistry
        self.shared_registry = SharedRegistry(self)
```

After `App.local()` (around line 530), add:

```python
    def shared[T](self, cls: type[T]) -> T:
        """Decorator: @app.shared @dataclass — register a cross-client reactive state class."""
        proxy = self.shared_registry.register(cls)
        return proxy  # type: ignore[return-value]
```

- [ ] **Step 3.4: Add `shared_set` dispatch to WS loop in `app.py`**

In the `websocket_endpoint` inner function, after the `if data.get("type") == "realtime":` block (around line 513), add:

```python
                    elif data.get("type") == "shared_set":
                        await self.shared_registry.handle_set(
                            client_id,
                            data.get("class", ""),
                            data.get("field", ""),
                            data.get("value"),
                        )
```

- [ ] **Step 3.5: Add shared state push to `SocketManager.connect()`**

In `SocketManager.connect()` (around line 290), after `await self.app.emit("connect", client_id)`, add:

```python
        await self.app.shared_registry.push_to_new_client(client_id)
```

Full updated method (push BEFORE emit so client has full state when on("connect") fires):
```python
    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        await self.app.shared_registry.push_to_new_client(client_id)
        await self.app.emit("connect", client_id)
```

- [ ] **Step 3.6: Run tests to confirm PASS**

```bash
uv run pytest tests/test_shared.py -v 2>&1 | tail -15
```

- [ ] **Step 3.7: Full suite check**

```bash
make 2>&1 | tail -5
```

- [ ] **Step 3.8: Commit**

```bash
git add violetear/app.py tests/test_shared.py violetear/shared.py
git commit -m "feat(shared): App.shared() decorator, WS shared_set dispatch, connect push"
```

---

### Task 4: transpile_class shared variant

**Files:**
- Modify: `violetear/transpile.py` — `transpile_class(cls, shared=False)`
- Modify: `tests/test_transpile.py` — add shared class emission tests

**Interfaces:**
- Consumes: existing `transpile_class(cls: type) -> str`
- Produces: `transpile_class(cls: type, shared: bool = False) -> str`
  - When `shared=True`: each setter also emits `if (!_shared._receiving) { _shared.set("ClassName", "fieldname", v); }`
  - Fields with `metadata={"server_only": True}` omit the `_shared.set(...)` line even when `shared=True`

- [ ] **Step 4.1: Write failing tests**

Add to `tests/test_transpile.py`:

```python
# Shared class transpilation
import dataclasses

def test_transpile_shared_class_setter_sends_shared_set():
    from violetear.transpile import transpile_class

    @dataclasses.dataclass
    class Shared:
        count: int = 0

    js = transpile_class(Shared, shared=True)
    assert '_shared.set("Shared", "count", v)' in js
    assert '_shared._receiving' in js

def test_transpile_shared_class_server_only_field_omits_shared_set():
    from violetear.transpile import transpile_class

    @dataclasses.dataclass
    class SharedWithReadonly:
        mutable: int = 0
        locked: str = dataclasses.field(default="x", metadata={"server_only": True})

    js = transpile_class(SharedWithReadonly, shared=True)
    # mutable field has shared_set
    assert '_shared.set("SharedWithReadonly", "mutable", v)' in js
    # locked field does NOT have shared_set
    assert '_shared.set("SharedWithReadonly", "locked", v)' not in js

def test_transpile_local_class_unchanged():
    from violetear.transpile import transpile_class

    @dataclasses.dataclass
    class Local:
        x: int = 0

    js = transpile_class(Local, shared=False)
    assert '_shared.set' not in js
```

- [ ] **Step 4.2: Run to confirm FAIL**

```bash
uv run pytest tests/test_transpile.py -k "shared" -v 2>&1 | head -20
```
Expected: `TypeError: transpile_class() got an unexpected keyword argument 'shared'`

- [ ] **Step 4.3: Modify `transpile_class` in `transpile.py`**

Change the function signature and the setter emission inside `transpile_class`. The current setter lines are around line 147–153. Change:

```python
def transpile_class(cls: type, shared: bool = False) -> str:
```

And update the setter loop — replace the `lines.append(...)` for the setter to conditionally include `_shared.set`:

```python
    for f in fields:
        ann = hints.get(f.name)
        checker = js_type_check(ann) if ann is not None else "_checkAny"
        lines.append(f"  get {f.name}() {{ return this._{f.name}; }}")
        is_server_only = dict(f.metadata).get("server_only", False)
        if shared and not is_server_only:
            setter_extra = (
                f' if (!_shared._receiving) {{ _shared.set("{class_name}", "{f.name}", v); }}'
            )
        else:
            setter_extra = ""
        lines.append(
            f"  set {f.name}(v) {{ "
            f"({checker})(v, \"{class_name}.{f.name}\"); "
            f"this._{f.name} = v; "
            f'ReactiveRegistry.notify("{class_name}.{f.name}", v);'
            f"{setter_extra} }}"
        )
```

- [ ] **Step 4.4: Run tests to confirm PASS**

```bash
uv run pytest tests/test_transpile.py -v 2>&1 | tail -10
```

- [ ] **Step 4.5: Full suite check**

```bash
make 2>&1 | tail -5
```

- [ ] **Step 4.6: Commit**

```bash
git add violetear/transpile.py tests/test_transpile.py
git commit -m "feat(shared): transpile_class shared=True emits _shared.set in setters"
```

---

### Task 5: runtime.js `_shared` object + WS dispatcher

**Files:**
- Modify: `violetear/runtime.js` — add `_shared` object and `_ws_send` helper; update `socket.onmessage`

**Interfaces:**
- Consumes: `_violetear_socket` (already in runtime.js); `_shared_objects` map (emitted by bundle gen in Task 6)
- Produces:
  - `_shared._receiving: boolean` — flag preventing echo during `shared_sync` handling
  - `_shared.set(cls, field, value)` — sends `shared_set` to server
  - `_shared.handle(msg)` — processes `shared_sync`
  - `_shared.handle_error(msg)` — logs `shared_error`
  - `_ws_send(payload_obj)` — queues JSON send; safe before socket open

No unit tests for JS (no test harness). The `test_examples_e2e.py` covers end-to-end. Manual verification via example 06.

- [ ] **Step 5.1: Add `_ws_send` helper to `runtime.js`**

Add after the `let _violetear_socket = null;` line (around line 388), before `_setup_websocket`:

```javascript
// Queue of messages to send when the socket opens.
let _ws_send_queue = [];

function _ws_send(obj) {
  const msg = JSON.stringify(obj);
  if (_violetear_socket && _violetear_socket.readyState === WebSocket.OPEN) {
    _violetear_socket.send(msg);
  } else {
    _ws_send_queue.push(msg);
  }
}
```

In `_setup_websocket`, inside `socket.onopen`, after the existing lifecycle dispatch, flush the queue:

```javascript
  socket.onopen = () => {
    // Flush any messages queued before the socket opened
    while (_ws_send_queue.length) {
      socket.send(_ws_send_queue.shift());
    }
    const handlers = scope._lifecycle?.connect ?? [];
    handlers.forEach(fn => fn().catch(e => console.error("[violetear] connect handler error:", e)));
  };
```

- [ ] **Step 5.2: Add `_shared` object to `runtime.js`**

Add after the `_ws_send` helper, before `_setup_websocket`:

```javascript
// ---------------------------------------------------------------------------
// _shared — handles shared_sync / shared_set for @app.shared state classes.
// _shared_objects is populated by bundle.js (generated per-app at startup).
// ---------------------------------------------------------------------------
let _shared_objects = {};  // overwritten by bundle.js

const _shared = {
  _receiving: false,

  set(cls, field, value) {
    _ws_send({ type: "shared_set", class: cls, field: field, value: value });
  },

  handle(msg) {
    const obj = _shared_objects[msg.class];
    if (!obj) {
      console.warn(`[violetear] shared_sync for unknown class: ${msg.class}`);
      return;
    }
    _shared._receiving = true;
    try {
      obj[msg.field] = msg.value;
    } catch (e) {
      console.error(`[violetear] shared_sync assignment error: ${e.message}`);
    } finally {
      _shared._receiving = false;
    }
  },

  handle_error(msg) {
    console.error(
      `[violetear] shared write rejected — ${msg.class}.${msg.field}: ${msg.reason}`
    );
  },
};
```

- [ ] **Step 5.3: Add `shared_sync` and `shared_error` cases to `socket.onmessage` in `runtime.js`**

In `_setup_websocket`, inside `socket.onmessage`, after the `if (data.type === "rpc")` block, add:

```javascript
    if (data.type === "rpc") {
      // ... existing rpc handling (unchanged) ...
    } else if (data.type === "shared_sync") {
      _shared.handle(data);
    } else if (data.type === "shared_error") {
      _shared.handle_error(data);
    }
```

- [ ] **Step 5.4: Verify runtime.js is syntactically valid**

```bash
node --check /home/apiad/Workspace/repos/violetear/violetear/runtime.js && echo "OK"
```
Expected: `OK` (no syntax errors)

- [ ] **Step 5.5: Full suite check**

```bash
make 2>&1 | tail -5
```

- [ ] **Step 5.6: Commit**

```bash
git add violetear/runtime.js
git commit -m "feat(shared): runtime.js _shared dispatcher + _ws_send queue"
```

---

### Task 6: Bundle generation — emit shared classes + `_shared_objects` map

**Files:**
- Modify: `violetear/app.py` — `App._generate_bundle_js()` (around line 606)
- Modify: `tests/test_unit.py` or `tests/test_shared.py` — bundle emission test

**Interfaces:**
- Consumes: `App.shared_registry._classes: dict[str, SharedProxy]`; `transpile_class(cls, shared=True)`
- Produces: bundle.js contains shared class JS + `_shared_objects = { ClassName: ClassName, ... };`

- [ ] **Step 6.1: Write failing test**

Add to `tests/test_shared.py`:

```python
def test_bundle_contains_shared_class_and_objects_map():
    from violetear.app import App
    import dataclasses

    app = App(title="test")

    @app.shared
    @dataclasses.dataclass
    class Score:
        value: int = 0

    bundle = app._generate_bundle_js()
    # Shared class emitted with _shared.set in setter
    assert '_shared.set("Score", "value", v)' in bundle
    # _shared_objects map emitted
    assert '_shared_objects = {' in bundle
    assert '"Score": Score' in bundle
```

- [ ] **Step 6.2: Run to confirm FAIL**

```bash
uv run pytest tests/test_shared.py -k "bundle" -v 2>&1 | head -20
```

- [ ] **Step 6.3: Update `_generate_bundle_js` in `app.py`**

In `_generate_bundle_js` (around line 606), after the `# 1. Compiled state classes` block, add a new block for shared classes:

```python
        # 1b. Shared state classes (transpiled with shared=True for WS setter)
        for cls_name, proxy in self.shared_registry._classes.items():
            instance = object.__getattribute__(proxy, "_instance")
            js = transpile_class(type(instance), shared=True)
            parts.append(js)

        # 1c. _shared_objects map — tells _shared.handle() which JS singletons to write
        if self.shared_registry._classes:
            entries = ", ".join(
                f'"{k}": {k}' for k in self.shared_registry._classes
            )
            parts.append(f"_shared_objects = {{{entries}}};")
```

Add this after the existing `for js in self.client._compiled_classes.values():` block.

- [ ] **Step 6.4: Run tests to confirm PASS**

```bash
uv run pytest tests/test_shared.py -v 2>&1 | tail -10
```

- [ ] **Step 6.5: Full suite check**

```bash
make 2>&1 | tail -5
```

- [ ] **Step 6.6: Commit**

```bash
git add violetear/app.py tests/test_shared.py
git commit -m "feat(shared): bundle emits shared classes + _shared_objects map"
```

---

### Task 7: Example 06 + roadmap update

**Files:**
- Create: `examples/06_shared.py`
- Modify: `roadmap.md` — add Phase 8 entry
- Modify: `tests/test_examples.py` — ensure example 06 is collected

**Interfaces:**
- Consumes: all prior tasks; `App`, `@app.shared`, `@dataclass`, `Document`, `StyleSheet`

- [ ] **Step 7.1: Create `examples/06_shared.py`**

```python
"""Tier 6 canonical example — shared state counter across all connected clients.

Demonstrates @app.shared: a reactive dataclass whose fields auto-broadcast
to every connected client. No manual broadcast calls. No request_history.
Open two browser tabs — clicking + in one tab updates the counter in both.

Run:
    python examples/06_shared.py

Then open http://localhost:8000 in two browser tabs.
"""
from dataclasses import dataclass, field

from violetear import App, Document, StyleSheet
from violetear.color import Colors
from violetear.js import DOM, Event
from violetear.units import px, rem

app = App(title="Shared Counter")


@app.shared
@dataclass
class Room:
    count: int = 0
    label: str = "clicks"
    server_version: str = field(
        default="1.0", metadata={"server_only": True}
    )


sheet = StyleSheet(normalize=True)
sheet.select("body").font(
    size=rem(1.0), family="system-ui, sans-serif"
).background(Colors.WhiteSmoke).padding(rem(2))
sheet.select(".card").rules(max_width="360px").margin("auto").background(
    Colors.White
).padding(rem(2)).rounded(px(8)).border(px(1), Colors.Gainsboro)
sheet.select(".count").font(size=rem(4), weight=700).color(Colors.Indigo).rules(
    text_align="center"
)
sheet.select(".btn").rules(
    display="block", width="100%", padding="12px",
    border="none", cursor="pointer", font_size="1.25rem",
    font_weight=700, margin_top="1rem",
).background(Colors.Indigo).color(Colors.White).rounded(px(6))
sheet.select(".label").font(size=rem(0.875)).color(Colors.SlateGray).rules(
    text_align="center", margin_top="0.25rem"
)


@app.client.callback
async def on_increment(event: Event):
    Room.count = Room.count + 1


@app.view("/")
def index():
    doc = Document(title="Shared Counter")
    doc.style(href="/style.css", sheet=sheet)

    with doc.body as body:
        with body.div(classes="card") as card:
            card.div(classes="count").text(Room.count)
            card.div(classes="label").text(Room.label)
            card.button(text="+1", classes="btn").on("click", on_increment)

    return doc


if __name__ == "__main__":
    app.run()
```

- [ ] **Step 7.2: Smoke-test the example renders without error**

```bash
uv run python -c "
import examples.06_shared as ex
doc = ex.index()
html = doc.render()
assert 'Shared Counter' in html
print('OK:', len(html), 'bytes')
"
```
Expected: `OK: <some number> bytes`

- [ ] **Step 7.3: Update `roadmap.md`**

Append to `roadmap.md`:

```markdown
## Phase 8: @app.shared — Realtime Cross-Client State Sync

- [ ] **SharedProxy + SharedRegistry**: server-side interception of field assignments; auto-broadcast via `SocketManager`
- [ ] **SocketManager**: `broadcast_shared_sync`, `send_shared_sync`, `send_shared_error`
- [ ] **App.shared() decorator**: registers `@app.shared @dataclass`; returns proxy singleton
- [ ] **WS dispatcher**: `shared_set` → `SharedRegistry.handle_set`; `shared_sync`/`shared_error` client-side
- [ ] **transpile_class(shared=True)**: setters emit `_shared.set(...)`; `server_only` fields skip it
- [ ] **runtime.js**: `_shared` object, `_ws_send` queue, `shared_sync`/`shared_error` handlers
- [ ] **Bundle generation**: shared classes + `_shared_objects` map emitted into bundle.js
- [ ] **Example 06**: counter shared across all tabs; demonstrates zero boilerplate
```

- [ ] **Step 7.4: Full suite check**

```bash
make 2>&1 | tail -5
```

- [ ] **Step 7.5: Commit**

```bash
git add examples/06_shared.py roadmap.md
git commit -m "feat(shared): example 06 shared counter + roadmap Phase 8"
```

- [ ] **Step 7.6: Push**

```bash
git push origin main
```
