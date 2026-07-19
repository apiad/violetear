# State Management

violetear's state model is built on one idea: **a Python `@dataclass` is the canonical definition of state**. Both per-session local state and cross-client shared state use the same primitive — a plain dataclass — and the framework generates the correct reactive glue automatically.

## @app.local — per-session reactive state

```python
from dataclasses import dataclass
from violetear.js import DOM

@app.local
@dataclass
class UiState:
    count: int = 0
    mode: str = "work"
    running: bool = False
```

`@app.local` compiles this dataclass to a **reactive JavaScript singleton**. Every field gets a setter that calls `ReactiveRegistry.notify(path, value)`, which immediately updates every DOM element bound to that field via `data-bind-*` attributes.

No stores. No signals. No event emitters. The dataclass is the store.

### Binding fields to the DOM

```python
@app.view("/")
def index():
    doc = Document(title="App")
    with doc.body as body:
        # Bind element text to UiState.count — updates automatically
        body.div().text(UiState.count)
        # Bind element class to UiState.mode
        body.div(classes=UiState.mode, text="Mode indicator")
    return doc
```

### Mutating state from client functions

```python
@app.client.callback
async def tick(event: Event):
    UiState.count = UiState.count + 1   # triggers DOM update
    UiState.mode = "rest" if UiState.count > 5 else "work"
```

---

## @app.shared — server-authoritative broadcast state

```python
from dataclasses import dataclass, field

@app.shared
@dataclass
class Room:
    count: int = 0
    messages: list = field(default_factory=list)
    # server_only=True: clients can read but cannot write
    version: str = field(default="1.0", metadata={"server_only": True})
```

`@app.shared` extends the same pattern across **all connected clients**. The dataclass instance lives on the server (in `SharedRegistry`). Any field assignment — whether from server-side code or a client callback — is intercepted by `SharedProxy.__setattr__`, which broadcasts a `shared_sync` WebSocket frame to every connection.

### Writing from a client callback

```python
@app.client.callback
async def increment(event: Event):
    Room.count = Room.count + 1
    # → sends shared_set to server
    # → server validates, re-broadcasts shared_sync to ALL clients
    # → every tab's DOM updates automatically
```

### Writing from server-side code

```python
@app.server.on("connect")
async def on_join(client_id: str):
    Room.count = Room.count + 1   # direct assignment, auto-broadcasts
```

---

## Comparison

| | `@app.local` | `@app.shared` |
|---|---|---|
| **Scope** | Per browser tab | All connected clients |
| **Lives in** | Browser JS singleton | Server `SharedRegistry` |
| **Mutation path** | setter → DOM update | setter → WS → server → broadcast → all DOM |
| **Persistence** | Optional (`localStorage`) | In-memory (per process) |
| **Conflict model** | N/A (isolated) | Last-write-wins |
| **Use for** | UI toggles, filters, form state | Chat, counters, collaborative tools |

---

## Key design decisions

**Server is the source of truth.** When a client writes a shared field, the write goes to the server first (`shared_set`), the server re-broadcasts (`shared_sync`) to all clients including the sender. The client never applies locally before the server confirms. Conflicts are impossible at the cost of one round-trip per mutation.

**Late-joiner push.** On every new WebSocket connection the server pushes one `shared_sync` frame per field before firing the application's `on("connect")` handler. New clients arrive with full state.

**Echo prevention.** When the client runtime handles an incoming `shared_sync`, it sets `_shared._receiving = true` which suppresses the setter's outbound `shared_set`. No echo loops.

**`server_only` fields.** Clients receive `shared_sync` for server-only fields (they can read the value and bind DOM to it) but their `shared_set` frames are rejected. The transpiler strips the `_shared.set()` call from the emitted setter.
