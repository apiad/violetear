---
number: 5
title: "Unified Server/Client Interaction API Refactoring"
state: open
labels:
---

## 1. Problem Description
The current API for defining client-side logic (`@app.client`, `@app.startup`) and server-side interactions (`@app.server`, `@app.connect`) is functional but lacks a cohesive structural philosophy.
* It is not immediately obvious which functions are RPC endpoints versus fire-and-forget signals.
* There is no unified way to handle custom events (e.g., "game_started", "user_joined") other than raw WebSocket hooks.
* Client-side DOM event handlers lack validation, leading to potential runtime errors if a user attaches a non-async or non-client function to an element.

## 2. Proposed Design
We will consolidate all interaction logic under two main namespaces: `@app.server` and `@app.client`. This creates a clear mental model: "Where does this code run?" and "How is it triggered?"

### 2.1 Server-Side API (`@app.server`)
Methods decorated here execute on the Python Backend (FastAPI).

* **`@app.server.rpc`**
    * **Behavior:** Exposed to the client via HTTP/Fetch.
    * **Contract:** Request/Response. The client `await`s this and receives a return value.
    * **Use Case:** Database queries, heavy computation, sensitive logic.

* **`@app.server.realtime`**
    * **Behavior:** Exposed to the client via WebSocket.
    * **Contract:** Fire-and-forget. The client calls this but **does not** wait for a result.
    * **Safety:** If the decorated function returns a value, the server logs a warning (data loss).
    * **Use Case:** High-frequency telemetry, keystrokes, broadcasting state updates.

* **`@app.server.on(event: str)`**
    * **Behavior:** Registers a handler for lifecycle or custom events.
    * **Lifecycle Events:** `"start"`, `"stop"`, `"connect"`, `"disconnect"`.
    * **Custom Events:** Triggered via `app.emit(event, data)`.

### 2.2 Client-Side API (`@app.client`)
Methods decorated here are transpiled/sent to the browser (Pyodide).

* **`@app.client`** (Base)
    * **Behavior:** Marks function for transpilation. Callable by other client-side code.

* **`@app.client.callback`**
    * **Behavior:** Specific marker for DOM Event Listeners.
    * **Validation:** The DOM binder (e.g., `div.on("click", func)`) must check for this decorator. If missing, raise `ValueError` to prevent runtime hydration errors.

* **`@app.client.realtime`**
    * **Behavior:** Registers the function as a target for Server-to-Client WebSocket calls (Reverse RPC).
    * **Contract:** Fire-and-forget. The server calls this to push updates to the browser.
    * **Use Case:** Updating UI based on server state changes, notifications.

* **`@app.client.on(event: str)`**
    * **Behavior:** Registers a handler for client-side events.
    * **Lifecycle Events:** `"ready"` (hydration done), `"connect"`, `"disconnect"`.

### 2.3 Runtime & Internals
* **`window.violetear`**: The JavaScript global object acting as the Single Source of Truth for the client.
* **`violetear.runtime`**:
    * **`get_runtime()`**: Returns a proxy to `window.violetear` (available only in Browser).
    * **`runtime.emit(event, data)`**: Allows Python client code to trigger the JS event bus.

## 3. Implementation Roadmap

### Phase 1: Core Refactoring (`violetear/app.py`)
- [ ] Create `Server` and `Client` nested classes within `App` to handle the new decorator syntax.
- [ ] Deprecate old decorators (`@app.startup`, `@app.connect`) in favor of lifecycle events (`@app.client.on("ready")`, `@app.server.on("connect")`).

### Phase 2: Event Bus & Runtime (`violetear/client.py`)
- [ ] Implement `window.violetear` in the JS bundle to manage event listeners.
- [ ] Implement `violetear.runtime` module for Python access to the event bus.
- [ ] Implement Message Queue: Ensure `emit` calls made before the socket connects are buffered and flushed upon connection.

### Phase 3: Communication Layer (`SocketManager`)
- [ ] Update `SocketManager` to distinguish between `rpc` (fetch) and `realtime` (websocket) messages.
- [ ] Implement the "Reverse RPC" mechanism for `@app.client.realtime`.

## 4. Considerations & Constraints
* **Serialization:** Events and Realtime calls are limited to JSON-serializable data.
* **Ambiguity:** Ensure strict warnings if a user tries to `await` a `realtime` function (client-side stubs should return `None`).
* **Execution Order:** Ensure handlers for `"ready"` and `"connect"` fire reliably regardless of network race conditions (client loads faster/slower than socket connects).