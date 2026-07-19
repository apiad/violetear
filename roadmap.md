# Violetear — Roadmap

**Status:** v2.0 released
**Current:** v2.0 — Python→JS compiler, no Pyodide, 85 tests pass

## Summary
`violetear` is a full-stack Python web framework. Server-Side Rendering via FastAPI, client-side logic compiled from Python to JavaScript at server startup (no Pyodide, no WASM). The core library stays zero-dependency; `violetear[server]` adds FastAPI + uvicorn.

## Phase 1: Modernization & Tooling
*Objective: Prepare the codebase for modern standards and faster iteration.*

- [x] **Dependency Update**: Bump minimum Python version to **3.12+**.
- [x] **Migrate to `uv`**: Replace `poetry` with `uv` for lightning-fast package management and CI/CD resolution.
- [x] **Project Structure**: Establish the folder structure for the new modules (`violetear.app`, `violetear.client`).

## Phase 2: The Framework Core (SSR Focus)
*Objective: Build a robust engine for serving Server-Side Rendered applications with zero unused CSS.*

### 2.1. Optional Server Dependencies
- [x] Add `fastapi` and `uvicorn` as optional extras (`pip install violetear[server]`).

### 2.2. The `App` Class (`violetear.app`)
- [x] **Initialization**: Create the `App` class that wraps a `FastAPI` instance.
- [x] **Routing**: Implement the `@app.route(path)` decorator.
    - Handle standard `GET` requests returning `Document` objects.
    - Handle standard `POST` form submissions.
- [x] **Asset Registry**: Implement `app.add_style(name, sheet)`.
    - Automatically mount a route to serve these rendered stylesheets from memory.
    - Provide helpers to inject `<link>` tags for registered styles into Documents.

### 2.3. Static Asset Handling
- [x] **Server Side**: Implement `app.mount_static(dir, path)` and auto-discover a `./static` folder.
- [x] **Markup Side**: Extend `Document` in `violetear/markup.py`:
    - Add `.link_css(url)` for CDNs/local files.
    - Add `.add_script(src)` for external JS.
- [x] **HTML Helpers**: Extend `Element` in `violetear/markup.py`:
    - Add `.link(href)` helper for anchors.
    - Add `.form(action, method)` and `.input()` helpers.

### 2.4. JIT "Atomic" CSS
- [ ] **Scanner**: Implement `Document.get_used_classes()` to scan the rendered element tree.
- [ ] **Filter**: Implement `StyleSheet.render_subset(classes)` in `violetear/stylesheet.py`.
- [ ] **Optimization**: Update `App.render_document` to inline *only* the used CSS for SSR routes, eliminating unused bytes.

### 2.5. Tailwind Preset
- [ ] Create `violetear.presets.Tailwind` class using `UtilitySystem`.
    - Pre-configure standard Tailwind scales (spacing, colors, typography).
    - Allow users to customize defaults (colors/screens) in the constructor.

## Phase 3: Interactivity (Isomorphic Python)
*Objective: Enable "Smart Hydration" where Python runs in the browser only when needed.*

### 3.1. Event Binding API (`violetear`)
- [x] Update `Element` to support event listeners.
    - Implement `.on("click", func)` and `.onclick(func)`.
    - **Server Behavior**: Serialize function name to `data-py-on-click` attribute.
    - **Client Behavior**: Bind the actual Python callable to the DOM.

### 3.2. Client Runtime (`violetear.client`)
- [x] **Hydration Script**: Create a generic Python script (to run in Pyodide) that:
    - Scans the DOM for `data-py-on-*` attributes.
    - Maps attributes to loaded Python functions from the user's bundle.
- [x] **RPC Stubs**: Create the client-side mechanism to intercept calls to `@app.server` functions and perform `fetch()` requests.

### 3.3. Smart Injection (`violetear.app`)
- [x] **Detection Logic**: Update `App` to inspect the generated `Document`.
    - If `data-py-on-*` attributes exist -> Inject Pyodide bootstrap + Client Bundle.
    - If no attributes exist -> Serve pure HTML (SSR Mode).

## Phase 4: PWA Integration
*Objective: Turn apps into installable software with offline capabilities.*

- [x] **Manifest Generator**: Create a class to generate `manifest.json` from `App` metadata.
- [x] **Route Configuration**: Add `pwa=True` parameter to `@app.view`.
    - Serves the manifest linked to that specific scope.
    - Injects `<meta>` tags for theme color and icons.
- [x] **Service Worker**: Implement a default Service Worker generator.
    - Automatically cache the Pyodide runtime and the app's registered CSS/JS assets (from the Asset Registry).

## Phase 5: v2.0 — Python→JS Compiler (Complete)

- [x] **Remove Pyodide**: replaced with `runtime.js` (~400 lines vanilla JS)
- [x] **`transpile.py`**: Python→JS AST compiler for state classes and client functions
- [x] **`violetear/js.py`**: browser API shims for IDE/mypy support
- [x] **`violetear/runtime.js`**: ReactiveRegistry, hydration, WebSocket, DOM, Storage, IDB
- [x] **Updated examples**: 03/04/05 use `from violetear.js import ...`

## Phase 6: Safe, self-verifying codegen (issue #8)

The one Python signature is the schema; validators are emitted on both ends of
every boundary (Pydantic server-side, our own zero-dep `_check` JS client-side).
No JS build tooling.

- [x] **Slice 1**: server→client realtime validated on both sides — server
  rejects mistyped `.broadcast`/`.invoke` kwargs; client runtime rejects a
  malformed inbound frame naming the field (`violetear/validate.py`,
  `_VALIDATORS` registry, `_check*` primitives in `runtime.js`).
- [x] **Slice 2**: client→server realtime + RPC arg/response validation — client
  send stubs validate args (RPC + realtime) and the RPC response; server rejects
  mistyped inbound realtime frames (`_RETURN_VALIDATORS`, `ServerRegistry._validate_incoming`).
- [x] **Slice 3**: reactive-setter field validation — each `@app.local` dataclass
  setter checks the assigned value against the field type before mutating +
  notifying (`transpile_class` + `validate.js_type_check`).
## Phase 7: Semantic soundness (issue #9)

Generated JS must *compute what the Python means*. A zero-dep `_py` runtime helper
the transpiler emits calls into (`if (_py.truthy(x))`, `_py.eq`, `_py.format`, …).

- [x] **Slice 1**: truthiness + deep equality + f-string format specs — `if`/
  `while`/ternary/`not`/`bool()` → `_py.truthy`; `and`/`or` → `_py.and`/`or`
  (thunked short-circuit); `==`/`!=` → `_py.eq`/`ne`; `f"{x:02d}"` → `_py.format`.
  Fixes the live example-04 time-display padding bug.
- [x] **Slice 2**: numeric/sequence — `%` (floored modulo), `*` (string/list
  repeat), `+` (list concat), `len()` (dict-aware), `str()` (Python repr) via
  `_py.mod`/`mul`/`add`/`len`/`str`. Augmented assignment (`+=`/`*=`/`%=`) on
  collections is a deferred follow-up (stays a JS operator for now).
- [x] **Slice 3**: membership — `in` / `not in` via `_py.contains` (string
  substring, array value-membership, dict key-membership). Was a compile error.

## Phase 8: @app.shared — Realtime Cross-Client State Sync

- [x] **SharedProxy + SharedRegistry**: server-side interception of field assignments; auto-broadcast via `SocketManager`
- [x] **SocketManager**: `broadcast_shared_sync`, `send_shared_sync`, `send_shared_error`
- [x] **App.shared() decorator**: registers `@app.shared @dataclass`; returns proxy singleton
- [x] **WS dispatcher**: `shared_set` → `SharedRegistry.handle_set`; `shared_sync`/`shared_error` client-side
- [x] **transpile_class(shared=True)**: setters emit `_shared.set(...)`; `server_only` fields skip it
- [x] **runtime.js**: `_shared` object, `_ws_send` queue, `shared_sync`/`shared_error` handlers
- [x] **Bundle generation**: shared classes + `_shared_objects` map emitted into bundle.js
- [x] **Example 06**: counter shared across all tabs; demonstrates zero boilerplate
