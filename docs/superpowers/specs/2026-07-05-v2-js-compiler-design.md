# violetear v2.0 — Python→JS Compiler + JS Runtime

**Status:** Spec — awaiting implementation plan  
**Version bump:** 1.2.4 → 2.0.0 (breaking)  
**Motivation:** Replace the 14MB Pyodide runtime with a Python→JS AST compiler and a small vanilla-JS runtime, enabling lightweight SPAs and landing pages while keeping Python as the sole authoring language.

---

## Summary of changes

| What | Before (v1) | After (v2) |
|---|---|---|
| Client runtime | Pyodide (~14MB WASM) | `runtime.js` (~400 lines vanilla JS) |
| Client code | Python executed in Pyodide | Python compiled to JS at server startup |
| Browser APIs | `from js import document` | `from violetear.js import DOM, sleep, ...` |
| Storage | `from violetear.storage import store` | `from violetear.js import localStorage` |
| Page load | `loadPyodide()` async startup | Two `<script>` tags, no async overhead |
| Pyodide download | ~14MB on first run | Removed entirely |

**What does NOT change:** all SSR (markup, stylesheet, Document DSL), server-side routing, WebSocket server, RPC endpoints, CSS DSL, PWA manifest generation, `@app.local` state for SSR initial values.

---

## 1. `violetear/js.py` — Python stubs for browser APIs

A new module named `violetear.js` (the `.js` suffix signals "you are writing client-side code"). Pattern identical to manifoldx's `shader.py`: correct type hints for IDE/mypy, `ClientOnlyError` raised if called server-side. The compiler strips `from violetear.js import X` imports inside client functions — every export is a global in `runtime.js`.

### Exports

**DOM manipulation**
```python
class DOMElement:
    text: str          # get/set → el.innerText
    html: str          # get/set → el.innerHTML
    value: Any         # get/set → el.value

    def add(self, *classes: str) -> "DOMElement": ...
    def remove(self, *classes: str) -> "DOMElement": ...
    def toggle(self, cls: str, force: bool | None = None) -> "DOMElement": ...
    def append(self, child: "DOMElement") -> "DOMElement": ...
    def attr(self, name: str, value: Any = None) -> "DOMElement | str | None": ...
    def on(self, event: str, handler) -> "DOMElement": ...
    def query(self, selector: str) -> list["DOMElement"]: ...

class DOM:
    @staticmethod def find(id: str) -> DOMElement: ...
    @staticmethod def create(tag: str) -> DOMElement: ...
    @staticmethod def query(selector: str) -> list[DOMElement]: ...
    @staticmethod def body() -> DOMElement: ...
```

**Events**
```python
class DatasetProxy:
    def __getattr__(self, name: str) -> str: ...

class EventTarget:
    value: str
    dataset: DatasetProxy

class Event:
    target: EventTarget
```

**Storage** — three tiers, all namespaced by `App(storage_prefix="myapp")` so multiple violetear apps on the same domain don't collide. Values are JSON-serialized transparently.

```python
class Storage:
    """Sync KV store backed by window.localStorage or window.sessionStorage."""
    def get(self, key: str, default=None) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...
    def remove(self, key: str) -> None: ...
    def has(self, key: str) -> bool: ...
    def clear(self) -> None: ...
    def __getattr__(self, key: str) -> Any: ...      # localStorage.foo → get("foo")
    def __setattr__(self, key: str, value: Any): ... # localStorage.foo = v → set("foo", v)

localStorage: Storage    # survives tab close
sessionStorage: Storage  # cleared on tab close

class IDBStore:
    """Async KV store backed by IndexedDB. Large quota, survives tab close."""
    async def get(self, key: str, default=None) -> Any: ...
    async def set(self, key: str, value: Any) -> None: ...
    async def remove(self, key: str) -> None: ...
    async def has(self, key: str) -> bool: ...
    async def keys(self) -> list[str]: ...
    async def items(self) -> list[tuple[str, Any]]: ...
    async def clear(self) -> None: ...
    # No attribute-style access — IDB ops are async; __getattr__ can't be awaited

idb: IDBStore  # app-namespaced singleton, good for offline-first apps (PWA)
```

`App(storage_prefix="myapp")` prefixes all keys for all three stores. If omitted, defaults to the app `title` slugified.

**Async / timing**
```python
async def sleep(seconds: float) -> None: ...
# Compiles to: await new Promise(r => setTimeout(r, seconds * 1000))
```

**Network**
```python
class FetchResponse:
    ok: bool
    status: int
    async def text(self) -> str: ...
    async def json(self) -> Any: ...

async def fetch(url: str, *, method: str = "GET", body: str | None = None,
                headers: dict | None = None) -> FetchResponse: ...
# Compiles to native JS fetch()
```

**Utilities**
```python
def get_client_id() -> str: ...
# Returns the per-tab UUID used to identify this WebSocket connection

class _Console:
    def log(self, *args) -> None: ...
    def error(self, *args) -> None: ...
    def warn(self, *args) -> None: ...

console: _Console

def exec(js_code: str) -> None: ...
# Escape hatch: emits js_code as a raw JS statement verbatim.
# Raises ClientOnlyError server-side.
# Example: exec("window.myLib.init()")
```

---

## 2. `violetear/runtime.js` — Vanilla JS runtime

Served at `/_violetear/runtime.js`. Replaces everything that ran inside Pyodide. Sets up globals that compiled code calls directly — no namespace prefix needed in compiled output.

### Globals provided

```javascript
// Reactive pub/sub
const ReactiveRegistry = {
    notify(path, value) { ... },
    bind(path, callback) { return unsubscribe_fn; }
};

// DOM helpers (match violetear.js stub API)
class DOMElement { ... }
const DOM = { find(id), create(tag), query(selector), body() };

// Storage (JSON-transparent localStorage/sessionStorage wrappers)
const localStorage = new Storage(window.localStorage);
const sessionStorage = new Storage(window.sessionStorage);

// Timing
async function sleep(seconds) {
    return new Promise(r => setTimeout(r, seconds * 1000));
}

// Fetch passthrough (native fetch, same signature)
// — no wrapper needed; native fetch is already global

// Client ID (per-tab UUID, module-scoped, not persisted)
function get_client_id() { ... }

// Escape hatch (compiles to eval, but name is reserved in runtime)
function exec(js_code) { eval(js_code); }

// Hydration entry point — called at end of bundle.js
function Violetear_hydrate(scope) {
    _hydrate_events(scope);
    _hydrate_bindings();
    _setup_websocket(scope);
    _dispatch_ready_event(scope);
}
```

### WebSocket / RPC internals

- Connects to `/_violetear/ws?client_id=<uuid>` on hydration
- On message `{ type: "rpc", func, args, kwargs }` → calls `scope[func](...args)`
- Auto-reconnects with 3s delay on close
- Fires registered `"connect"` / `"disconnect"` lifecycle handlers

### Hydration

Scans DOM for:
- `data-on-<event>="fn_name"` → `el.addEventListener(event, scope[fn_name])`
- `data-bind-<prop>="StateName.field"` → `ReactiveRegistry.bind(path, updater_fn)`

---

## 3. `violetear/transpile.py` — Python→JS AST compiler

### Error type

```python
class ClientCompileError(Exception):
    category: str   # "unsupported-construct", "missing-annotation", "recursion", ...
    message: str
    filename: str
    line: int
    col: int
    source_line: str | None
```

### `transpile_class(cls: type) -> str`

For `@app.local @dataclass` classes. Reads live `__annotations__` + `__dataclass_fields__` defaults.

**Python default → JS default:**
- `int` / no default → `0`
- `float` → `0.0`
- `str` → `""`
- `bool` → `false`
- `list` → `[]`
- `dict` → `{}`
- Literal default (e.g. `1500`, `"work"`, `True`) → emitted verbatim

**Output pattern — singleton keeps the original class name so Python code translates 1:1:**
```javascript
class _ClassName {  // internal constructor, underscore-prefixed
    constructor() {
        this._field1 = <default1>;
        this._field2 = <default2>;
    }
    get field1() { return this._field1; }
    set field1(v) { this._field1 = v; ReactiveRegistry.notify("ClassName.field1", v); }
    // ...
}
const ClassName = new _ClassName();
// User writes UiState.meters in both Python and JS — no name translation needed.
```

**Rejected:** methods on state classes (use `@app.client` functions instead).

### `transpile_function(fn) -> str`

For `@app.client`, `@app.client.callback`, `@app.client.realtime`, `@app.client.on(event)`.

Reads source via `inspect.getsource` + `textwrap.dedent`. Strips all decorator lines. Compiles the `async def` body.

**Supported statements:**

| Python | JavaScript |
|---|---|
| `x = expr` | `let x = expr;` (first occurrence) / `x = expr;` (reassignment) |
| `x: T = expr` | `let x = expr;` |
| `x += expr` | `x += expr;` (etc. for all augmented ops) |
| `if cond: ...` | `if (cond) { ... }` |
| `elif cond: ...` | `else if (cond) { ... }` |
| `else: ...` | `else { ... }` |
| `for x in range(n)` | `for (let x = 0; x < n; x++) { ... }` |
| `for x in range(a, b)` | `for (let x = a; x < b; x++) { ... }` |
| `for k, v in d.items()` | `for (const [k, v] of Object.entries(d)) { ... }` |
| `for x in lst` | `for (const x of lst) { ... }` |
| `while cond: ...` | `while (cond) { ... }` |
| `return expr` | `return expr;` |
| `return` | `return;` |
| `try: ... except (E1, E2): body` | `try { ... } catch(e) { body }` (exception type ignored) |
| `import X` / `from X import Y` | stripped entirely (all symbols are globals) |
| `await expr` | `await expr;` |
| `break` / `continue` | `break;` / `continue;` |

**Supported expressions:**

| Python | JavaScript |
|---|---|
| `None` / `True` / `False` | `null` / `true` / `false` |
| Integer / float / string literals | verbatim |
| f-string `f"hello {x}"` | template literal `` `hello ${x}` `` |
| `x + y`, `x - y`, `x * y`, `x / y`, `x % y` | same |
| `x // y` | `Math.floor(x / y)` |
| `x ** y` | `Math.pow(x, y)` |
| `x == y`, `x != y`, `<`, `>`, `<=`, `>=` | `===`, `!==`, `<`, `>`, `<=`, `>=` |
| `x is None` / `x is not None` | `x === null` / `x !== null` |
| `x and y`, `x or y`, `not x` | `x && y`, `x \|\| y`, `!x` |
| `a if cond else b` | `(cond ? a : b)` |
| `obj.attr` | `obj.attr` |
| `obj[key]` | `obj[key]` |
| `obj.method(args)` | `obj.method(args)` |
| `[1, 2, 3]` | `[1, 2, 3]` |
| `{"key": val}` | `{key: val}` |
| `(a, b)` | `[a, b]` (tuple → array) |
| `await expr` | `await expr` |

**Built-in function translations:**

| Python | JavaScript |
|---|---|
| `int(x)` | `Math.trunc(Number(x))` |
| `float(x)` | `Number(x)` |
| `str(x)` | `String(x)` |
| `bool(x)` | `Boolean(x)` |
| `len(x)` | `x.length` |
| `print(x)` | `console.log(x)` |
| `abs(x)` | `Math.abs(x)` |
| `round(x)` | `Math.round(x)` |
| `round(x, n)` | `parseFloat(x.toFixed(n))` |
| `min(a, b)` | `Math.min(a, b)` (scalar only; list form rejected) |
| `max(a, b)` | `Math.max(a, b)` (scalar only) |
| `pow(x, y)` | `Math.pow(x, y)` |
| `sum(lst)` | rejected — use a for loop |
| `isinstance(x, T)` | rejected — raises `ClientCompileError` |
| `exec(s)` (from violetear.js) | raw `s` emitted as JS statement |

**String method translations:**

| Python | JavaScript |
|---|---|
| `.strip()` | `.trim()` |
| `.upper()` | `.toUpperCase()` |
| `.lower()` | `.toLowerCase()` |
| `.startswith(s)` | `.startsWith(s)` |
| `.endswith(s)` | `.endsWith(s)` |
| `.split(sep)` | `.split(sep)` |
| `.join(lst)` | `lst.join(sep)` (reversed receiver — compiler rewrites) |
| `x[:n]` | `x.slice(0, n)` |
| `x[n:]` | `x.slice(n)` |
| `x[a:b]` | `x.slice(a, b)` |

**Rejected (with clear error):**
- List/dict/set comprehensions
- Lambda
- `*args` / `**kwargs`
- Generators / `yield`
- `with` statement
- Nested `class` or `def` inside a function
- Non-`async` functions (client handlers must be async)
- Walrus operator (`:=`)
- Multi-target assignment (`a = b = c`)
- `raise` (use early `return` instead)
- `global` / `nonlocal`
- `assert`

---

## 4. `violetear/app.py` changes

### Removed
- `PYODIDE_VERSION`, `PYODIDE_FILES`, `PYODIDE_CDN_BASE` constants
- `_pyodide_cache_dir()`, `_ensure_pyodide_cached()`, `_pyodide_download_lock`
- `GET /_violetear/pyodide/{filename}` route
- `GET /_violetear/bundle.py` route
- `_generate_bundle()` (Python bundle generator)
- All `inspect.getsource` calls in `ClientRegistry` (replaced by `transpile_*`)

### Added
- `GET /_violetear/runtime.js` → serve `violetear/runtime.js` (static, cached)
- `GET /_violetear/bundle.js` → serve `_generate_bundle_js()` result
- `_generate_bundle_js() -> str` — concatenates:
  1. Compiled state class JS (from `self.client._compiled_classes`)
  2. Compiled function JS (from `self.client._compiled_functions`)
  3. JS RPC stubs for `@app.server.rpc` functions
  4. JS realtime stubs for `@app.server.realtime` functions
  5. `Violetear_hydrate(scope)` call with scope object referencing all compiled names

### Modified

**`App.local(cls)`** — calls `transpile_class(cls)` at decoration time; stores result; raises `ClientCompileError` immediately on any unsupported construct.

**`ClientRegistry.callback/realtime/on/bare`** — calls `transpile_function(fn)` at decoration time; stores result.

**`_inject_client_side(doc)`** — replaces Pyodide injection:
```python
doc.script(src="/_violetear/runtime.js")
doc.script(src=self._version_url("/_violetear/bundle.js"))
```
No inline bootstrap needed — bundle.js calls `Violetear_hydrate` at module level.

### JS RPC stub pattern (generated)

```javascript
// @app.server.rpc
async function precise_convert({meters}) {
    const r = await fetch("/_violetear/rpc/precise_convert", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({meters})
    });
    if (!r.ok) throw new Error(`RPC error: ${r.status}`);
    return r.json();
}

// @app.server.realtime
async function post_message({client_id, text}) {
    window.violetear_socket.send(JSON.stringify({
        type: "realtime", func: "post_message",
        args: [], kwargs: {client_id, text}
    }));
}
```

---

## 5. Interaction patterns — wire protocol

### Scope object

The bundle.js ends with a scope object passed to `Violetear_hydrate`. The bundle generator builds it from the registered decorators:

```javascript
const scope = {
    // Lifecycle handlers grouped by event name
    _lifecycle: {
        connect:    [on_socket_connect],
        disconnect: [],
        ready:      [on_ready, restore],
    },
    // @app.client.realtime — pushed from server by name
    receive_message,
    set_user_list,
    receive_history,
    // @app.client.callback / @app.client / bare — DOM events and helpers
    on_send_click,
    on_rename_click,
    save_state,
    tick,
};
Violetear_hydrate(scope);
```

### `@app.server.rpc` — HTTP round-trip

Server function unchanged. Client call `await precise_convert(meters=m)` → JS fetch stub. Compiler resolves Python kwargs to positional using the registered server signature at compile time.

```javascript
async function precise_convert(meters) {
    const r = await fetch("/_violetear/rpc/precise_convert", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({meters})
    });
    if (!r.ok) throw new Error(`RPC ${r.status}`);
    return r.json();
}
```

### `@app.server.realtime` — fire-and-forget via WebSocket

```javascript
async function post_message(client_id, text) {
    window.violetear_socket.send(JSON.stringify({
        type: "realtime", func: "post_message",
        args: [], kwargs: {client_id, text}
    }));
}
```

### `@app.client.realtime` — server pushes to client

Server sends `{type:"rpc", func:"receive_message", kwargs:{msg:{...}}}`.  
Runtime calls `scope["receive_message"](kwargs)`.  
Compiled function uses destructured params to match kwargs:

```python
# User writes:
@app.client.realtime
async def receive_message(msg: dict): ...

# Compiler emits:
async function receive_message({msg}) { ... }
# Called by runtime as: receive_message(data.kwargs)
```

### `broadcast` / `invoke` — server side only, no client changes

`receive_message.broadcast(msg=msg)` sends the WebSocket frame to all/one client. Runtime dispatches to the compiled function. No client-side design change.

### `@app.client.on("connect")` / `@app.client.on("ready")`

Registered in `scope._lifecycle`. Runtime dispatches:
- `connect`: when WebSocket `onopen` fires
- `ready`: after `_hydrate_events` + `_hydrate_bindings` complete
- `disconnect`: when WebSocket `onclose` fires (before reconnect attempt)

### `@app.client.callback` — DOM event handlers

Attached via `data-on-<event>="fn_name"` attributes (set during SSR). Runtime: `el.addEventListener(event, scope[fn_name])`. No `create_proxy` needed — native JS functions attach directly.

---

## 6. Files deleted / repurposed

| File | Fate |
|---|---|
| `violetear/client.py` | **Deleted** — replaced by `runtime.js` |
| `violetear/dom.py` | **Replaced** — keep as thin server-side stub (raises `ClientOnlyError`); or remove entirely since users now import from `violetear.js` |
| `violetear/storage.py` | **Replaced** — same; keep as deprecated stub or remove |
| `violetear/js.py` | **New** — the shim module |
| `violetear/runtime.js` | **New** — the JS runtime |
| `violetear/transpile.py` | **New** — the AST compiler |

`violetear/state.py` — keep unchanged; `ReactiveProxy` is still used server-side to track state mutations during SSR.

---

## 6. Updated examples

All 5 canonical examples need import updates:

```python
# Before (v1)
from violetear.dom import DOM, Event
from violetear.storage import store
from violetear.client import get_client_id
import asyncio  # inside function body

# After (v2)
from violetear.js import DOM, Event, localStorage, get_client_id, sleep
```

Specific changes:
- `store.X` → `localStorage.X`
- `await asyncio.sleep(1)` → `await sleep(1)` (seconds, same convention)
- `from violetear.client import get_client_id` → already imported from `violetear.js`

---

## 7. Breaking changes summary

1. Pyodide removed — `pip install violetear[server]` no longer downloads Pyodide assets
2. `violetear.dom`, `violetear.storage`, `violetear.client` are removed or deprecated — use `violetear.js`
3. `from js import ...` no longer works in client code (was Pyodide-specific)
4. `create_proxy`, `to_js` and other Pyodide FFI calls removed
5. Client handler functions must be `async def` (was informally required; now enforced by compiler)
6. Only the supported Python subset compiles — unsupported constructs raise `ClientCompileError` at server startup
7. `import asyncio; await asyncio.sleep(n)` → `from violetear.js import sleep; await sleep(n)`
8. PWA service worker cache list no longer includes Pyodide files — simpler and much smaller

---

## Implementation slices (for writing-plans)

Suggested order to keep a working app at each step:

1. **`transpile.py` — state classes only** (no function compiler yet; compile `@app.local` classes, verify reactive JS output)
2. **`runtime.js` — core runtime** (ReactiveRegistry, hydration, WebSocket; no DOM yet just the wiring)
3. **`app.py` — wire compiler into bundle endpoint** (serve runtime.js + bundle.js; page loads with reactive state but no event handlers yet)
4. **`transpile.py` — function compiler** (full supported subset; one example at a time: 03 → 04 → 05)
5. **`violetear/js.py` — shim module** (typed stubs; update examples to use new imports)
6. **Delete Pyodide machinery** (remove download code, old routes, old bundle endpoint)
7. **Update all 5 examples** (use `from violetear.js import ...`; verify each runs)
8. **Version bump to 2.0.0** (`make release` after all examples pass)
