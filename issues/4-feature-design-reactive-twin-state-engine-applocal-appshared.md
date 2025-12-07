---
number: 4
title: "Feature Design: Reactive Twin-State Engine (@app.local & @app.shared)"
state: open
labels:
---

# Feature Design: Reactive Twin-State Engine

**Target Version:** v1.4
**Status:** Draft

This document outlines the design for a comprehensive state management system that splits application state into two distinct lifecycles: **Local (Client-Side)** and **Shared (Real-Time Server-Side)**. This eliminates the need for external state management libraries or manual WebSocket wiring.

## Objective
Provide two decorators, `@app.local` and `@app.shared`, that allow developers to define state objects. Violetear will handle the synchronization, reactivity, and persistence transparently.

These two decorators must provide type hints that make the IDE believe we have objects (can be Pydantic objects in the server), so we can use the decorated function as if it were the actual state object.

## 1. Local State (`@app.local`)

**Concept:** Reactive state that lives exclusively in the browser for a single user session.

### 1.1 Behavior
* **Initialization:** The decorated function runs *once* on the server to provide the initial default values (hydrated into the bundle).
* **Persistence:** Optionally backed by `localStorage` (session persistence) via a `persist=True` flag.
* **Reactivity:** Changes to the state object in the client automatically trigger updates to bound DOM elements.
* **Scope:** Unique per browser tab/window.

### 1.2 Implementation
* **Decorator:** Registers the function and returns a `ClientState` proxy.
* **Client Proxy:** Uses `Proxy` (JS) or `__setattr__` (Python) to intercept writes and update the DOM.

```python
@app.local
def ui_state():
    return {"theme": "light", "sidebar_open": False}

# Usage
def toggle_sidebar(event):
    ui_state.sidebar_open = not ui_state.sidebar_open
```

## 2. Shared State (`@app.shared`)

**Concept:** Real-time state that lives on the server and is synchronized across *all* connected clients.

### 2.1 Behavior

  * **Single Source of Truth:** The state lives in the server's memory (or a Redis backend in the future).
  * **Broadcasting:** When *any* client modifies this state, the change is sent to the server via WebSocket.
  * **Propagation:** The server validates the change and broadcasts the new value to all other connected clients.
  * **Conflict Resolution:** Last-write-wins (initially) or operational transformation (future).

### 2.2 Implementation

  * **WebSocket Endpoint:** `App` must mount a `/_violetear/ws` endpoint.
  * **Server Proxy:** Intercepts writes in Python (Server), updates the central store, and pushes updates to the WebSocket manager.
  * **Client Proxy:** Intercepts writes in Pyodide (Client), sends JSON payloads over the WebSocket, and listens for incoming updates to update the local DOM.

```python
@app.shared
def chat_room():
    return {"messages": [], "active_users": 0}

# Usage
def send_msg(msg):
    # Updates server state -> Broadcasts to all users -> Updates their DOM
    chat_room.messages.append(msg)
```

## 3. Integration Architecture

### 3.1 The WebSocket Manager (`violetear.app.App`)

  * Needs to track active connections.
  * Needs a protocol for `SYNC` messages (e.g., `{"store": "chat_room", "key": "messages", "value": [...]}`).

### 3.2 The Client Runtime

  * **Startup:** On load, establish WebSocket connection.
  * **Resync:** On reconnection, request full state dump from server.

## 4. Usage Example

```python
@app.shared
def game_state():
    return {"score": 0}

@app.local
def player_state():
    return {"name": "Player 1"}

@app.client
def score_point(event):
    # Updates globally
    game_state.score += 1
    # Updates locally
    print(f"{player_state.name} scored!")
```

## 5. Task List

**Core**

  - [ ] Implement `WebSocketManager` in `App` (using FastAPI websockets).
  - [ ] Create `SharedState` proxy class (Server-side).
  - [ ] Create `LocalState` proxy class (Client-side).

**Client-Side**

  - [ ] Add WebSocket connection logic to `client.py` / bundle.
  - [ ] Implement the `SYNC` protocol handler in Pyodide.

**Decorators**

  - [ ] Implement `@app.local`.
  - [ ] Implement `@app.shared`.