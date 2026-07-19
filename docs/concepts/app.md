# Full-Stack App

## App initialization

```python
from violetear import App

app = App(
    title="My App",
    version="1.0.0",        # pin for stable PWA cache keys
    storage_prefix="myapp", # namespace for localStorage keys
)
```

## Routes

```python
from violetear.markup import Document

@app.view("/")
def index():
    doc = Document(title="Home")
    # ... build document ...
    return doc
```

## Serving stylesheets

```python
from violetear import StyleSheet

sheet = StyleSheet()
# ... define styles ...

app.style("/style.css", sheet)   # register at this path

@app.view("/")
def index():
    doc = Document(title="Home")
    doc.head.link_css("/style.css")  # inject <link> tag
    return doc
```

## Client functions

```python
from violetear.js import Event

@app.client.callback        # safe for DOM event handlers
async def handle_click(event: Event):
    ...

@app.client.on("ready")    # runs after DOMContentLoaded
async def on_ready():
    ...

@app.client.on("connect")  # runs when WebSocket connects
async def on_connect():
    ...

@app.client                 # generic compiled function
async def helper():
    ...
```

## Server functions

```python
@app.server.rpc
async def save(name: str, value: int) -> dict:
    # Called from client via RPC (HTTP POST under the hood)
    return {"status": "ok"}

@app.server.realtime
async def push_event(message: str):
    # Can be called client-side via WebSocket
    ...

@app.server.on("startup")
async def on_startup():
    ...
```

## Running

```python
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

Or with uvicorn directly:

```bash
uvicorn myapp:app.api --reload
```
