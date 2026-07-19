# Real-Time & Shared State

## Server → Client broadcasts

`@app.client.realtime` defines a function that runs in the browser but can be invoked by the server:

```python
@app.client.realtime
async def update_alert(message: str, color: str):
    from violetear.js import DOM
    el = DOM.find("status")
    el.text = message
    el.add_class(color)
```

```python
@app.server.on("connect")
async def greet(client_id: str):
    # Invoke on one specific client
    await update_alert.invoke(client_id, message="Welcome!", color="green")

# Or broadcast to everyone
await update_alert.broadcast(message="Server restarting…", color="red")
```

## @app.shared — multiplayer state

See [State Management → @app.shared](state.md#appshared--server-authoritative-broadcast-state).

## WebSocket lifecycle

```python
@app.server.on("connect")
async def on_join(client_id: str):
    print(f"Client {client_id} joined")

@app.server.on("disconnect")
async def on_leave(client_id: str):
    print(f"Client {client_id} left")

@app.client.on("connect")
async def on_connected():
    from violetear.js import DOM
    DOM.find("status").text = "Connected"

@app.client.on("disconnect")
async def on_disconnected():
    from violetear.js import DOM
    DOM.find("status").text = "Reconnecting…"
```

!!! note
    Don't broadcast from `@app.server.on("startup")`. At startup there are zero active WebSocket connections — any broadcast there silently no-ops.
