<div style="text-align: center;">
  <img src="https://github.com/apiad/violetear/blob/main/logo.png?raw=true" height="200px" style="border-radius:5px;">
</div>

**The Full-Stack Web Framework for Pythonistas.**

<!-- Project badges -->
![PyPI - Version](https://img.shields.io/pypi/v/violetear)
![PyPi - Python Version](https://img.shields.io/pypi/pyversions/violetear)
![PyPi - Downloads (Monthly)](https://img.shields.io/pypi/dm/violetear)
![Github - Commits](https://img.shields.io/github/commit-activity/m/apiad/violetear)


`violetear` is a minimalistic yet fully capable framework for building modern web applications in **pure Python**. It eliminates the context switch between backend and frontend by allowing you to write your styles, your markup, and your client-side logic all in the language you love.

It features a unique 3-layer architecture:

1.  **🎨 Styling Layer**: Generate CSS rules programmatically with a fluent, pythonic API. Includes an **Atomic CSS** engine that generates utility classes on the fly.
2.  **🧱 UI Layer**: Build reusable HTML components with a fluent builder pattern. Type-safe, refactor-friendly, and composable.
3.  **⚡ Logic Layer**: Write server-side and client-side code in the same file. `violetear` handles the compilation, bundling, RPC bridges, and state persistence seamlessly.

Use it for anything: from a simple script to generate a CSS file, to a static site generator, all the way up to a full-stack Isomorphic Web App powered by **FastAPI** and a **Python→JS compiler** (no Pyodide, no WASM, no 14MB download).

## 📦 Installation

To use the core library (HTML/CSS generation only), install the base package:

```bash
pip install violetear
````

To build full-stack applications (with the App Engine and Server), install the server extras:

```bash
pip install "violetear[server]"
```

## 🚀 Quickstart: The Isomorphic Counter

Let's build a fully interactive "Counter" app. The state persists across reloads using **Local Storage**, updates instantly in the browser via the **DOM API**, and syncs with the server via **RPC**.

**Zero JavaScript required.**

### 1. Initialize the App

First, we create the application instance. This wraps FastAPI to provide a powerful client-server isomorphic engine.

```python
from violetear import App

app = App(title="Violetear Counter")
```

### 2. Define Styles (CSS-in-Python)

Instead of writing CSS strings, use the fluent API to define your theme.

```python
from violetear import StyleSheet
from violetear.color import Colors
from violetear.style import Style

# Create a global stylesheet
style = StyleSheet()

style.select("body").background(Colors.AliceBlue).font(family="sans-serif") \
     .flexbox(align="center", justify="center").height("320px").margin(top=20)

style.select(".counter-card").background(Colors.White).padding(40).rounded(15) \
     .shadow(blur=20, color="rgba(0,0,0,0.1)").text(align="center")

style.select(".count-display").font(size=64, weight="bold").color(Colors.SlateBlue).margin(10)

style.select("button").padding("10px 20px").font(size=20, weight="bold") \
     .margin(5).rounded(8).border(0).rule("cursor", "pointer").color(Colors.White)

style.select(".btn-plus").background(Colors.MediumSeaGreen)
style.select(".btn-minus").background(Colors.IndianRed)
style.select(".btn:hover").rule("opacity", "0.8")
```

### 3. Server Logic (RPC)

Define a function that runs on the server. The `@app.server.rpc` decorator exposes this function so your client code can call it directly.

```python
@app.server.rpc
async def report_count(current_count: int, action: str):
    """
    This runs on the SERVER.
    FastAPI automatically validates that current_count is an int.
    """
    print(f"[SERVER] Count is now {current_count} (Action: {action})")
    return {"status": "received"}
```

### 4. Client Logic (In-Browser Python)

Define the interactivity. We use `@app.client.on("ready")` to restore state when the page loads and everything is setup.

> **v2.0:** Client-side Python is now compiled to JavaScript at server startup. Import browser APIs from `violetear.js` — these are type-correct stubs for IDE/mypy support that become JS globals in the browser.

```python
@app.client.on("ready")
async def init_counter():
    """
    Runs automatically when the page loads (Client-Side).
    Restores the counter from Local Storage so F5 doesn't reset it.
    """
    from violetear.js import DOM, localStorage

    # We can access storage like an object!
    saved_count = localStorage.count
    if saved_count is not None:
        DOM.find("display").text = str(saved_count)
```

And we use `@app.client.callback` to handle user interactions. The code is compiled to JavaScript at server startup — no Pyodide, no 14MB WASM download. We can also call server-side functions seamlessly, via automagic RPC (Remote Procedure Call).

```python
from violetear.js import Event

@app.client.callback
async def handle_change(event: Event):
    """
    Compiled to JavaScript and runs in the browser on click.
    """
    from violetear.js import DOM, localStorage

    # A. Get current state from DOM
    display = DOM.find("display")
    current_value = int(display.text)

    # B. Determine action
    action = event.target.id  # "plus" or "minus"
    new_value = current_value + (1 if action == "plus" else -1)

    # C. Update DOM immediately (Responsive)
    display.text = str(new_value)

    # D. Save to Local Storage (Persistence)
    localStorage.count = new_value

    # E. Sync with Server (Background)
    await report_count(current_count=new_value, action=action)
```

### 5. The UI (Server-Side Rendered)

Finally, create the route that renders the initial HTML. We attach the style and bind the Python function to the button's click event.

```python
from violetear.markup import Document, HTML

@app.view("/")
def index():
    doc = Document(title="Violetear Counter")

    # Auto-serve our generated CSS at this URL
    doc.style(style, href="/style.css")

    doc.body.add(
        HTML.div(classes="counter-card").extend(
            HTML.h2(text="Isomorphic Counter"),
            # The Count
            HTML.div(id="display", classes="count-display", text="0"),
            # Controls - Both call the same Python function
            HTML.button(id="minus", text="-", classes="btn-minus btn").on(
                "click", handle_change
            ),
            HTML.button(id="plus", text="+", classes="btn-plus btn").on(
                "click", handle_change
            ),
            HTML.p(text="Refresh the page! The count persists.").style(
                Style().color(Colors.Gray).margin(top=20)
            ),
        )
    )

    return doc

if __name__ == "__main__":
    app.run()
```

Run it with `python main.py` and open `http://localhost:8000`. You have a full-stack, styled, interactive app with persistence in 70 lines of pure Python!

## ✨ Features

### 🎨 Powerful Styling Engine

  * **Fluent API**: `style.select("div").color(Colors.Red).margin(10)`
  * **Type-Safe Colors**: Built-in support for RGB, HSL, Hex, and a massive library of standard web colors (`violetear.color.Colors`).
  * **Presets**:
      * **Atomic CSS**: A complete Tailwind-compatible utility preset. Generate thousands of utility classes (`p-4`, `text-xl`, `hover:bg-red-500`) purely in Python.
      * `FlexGrid` & `SemanticDesign` included.

### 🧱 Component System

  * **Declarative Builder**: Create HTML structures without writing HTML strings.
  * **Reusability**: Subclass `Component` to create reusable widgets (Navbars, Cards, Modals) that encapsulate their own structure and logic.

### ⚡ Full-Stack Application Engine

  * **Hybrid Architecture**: Supports both **Server-Side Rendering (SSR)** for SEO and speed, and **Client-Side Rendering (CSR)** for interactivity.
  * **Python→JS Compiler**: Client-side Python functions (`@app.client.*`) are compiled to JavaScript at server startup via an AST compiler. No Pyodide, no WASM, no 14MB download.
  * **Browser API stubs**: `violetear.js` provides type-correct Python stubs (`DOM`, `localStorage`, `sessionStorage`, `sleep`, `fetch`) for IDE and mypy support. Every export is a JS global in the runtime.
  * **Asset Management**: Stylesheets created in Python are served directly from memory.
  * **Seamless RPC**: Call server functions from the browser as if they were local.

## 📱 Progressive Web App (PWA) Support

Violetear allows you to turn any route into an installable PWA. This enables your app to:

1.  **Be Installed:** Users can add it to their home screen (mobile/desktop).
2.  **Work Offline:** The app shell and assets are cached automatically.
3.  **Auto-Update:** Changes to your Python code are detected, ensuring users always see the latest version.

### How to Enable PWA

Simply pass `pwa=True` (or a `Manifest` object) to the `@app.view` decorator.

**Important:** You must define an app `version`. If you don't, Violetear generates a random one on every restart, which will force users to re-download the app every time you deploy.

```python
# 1. Set a version string (e.g., from git commit or semantic version)
app = App(title="My App", version="v1.0.2")

# ...

# 2. Enable PWA on your desired route
@app.view("/", pwa=Manifest(
    name="My Super App",
    short_name="SuperApp",
    description="An amazing Python PWA",
    theme_color="#6b21a8"
))
def home():
    return Document(...)
```

The "application" cache is defined per route (@app.view), so you can have multiple PWAs served from the same violetear application. You can setup some routes for delivering PWA-enables app while other routes serve server-side rendered documents or standard (non-PWA) dynamic documents. You can match and mix as you wish.

### Caching Strategy

Violetear uses a hybrid strategy to ensure safety and speed:

  * **Navigation (HTML):** *Network-First*. It tries to fetch the latest version from the server. If offline, it falls back to the cache.
  * **Assets (JS/CSS):** *Cache-First*. Assets are versioned (e.g., `bundle.js?v=2.0.0`). This ensures instant loading while guaranteeing updates when the version changes.

### Current Limitations

  * **Push Notifications:** Not yet supported, and unclear if we ever will.
  * **Background Sync:** Offline actions (like submitting a form while disconnected) are not automatically retried when online. You must handle connection errors manually in your client logic. At some time we may provide a standard mechanism for queueing this type of actions.

## 📡 Real-Time: Server Broadcasts

Violetear supports **Reverse RPC**, allowing the server to call functions running in the user's browser. This is perfect for real-time notifications, live feeds, or multiplayer games.

The magic happens via the `.broadcast()` method available on any `@app.client` function.

### 1. Define the Client Function

Create a function decorated with `@app.client.realtime`. This code will be compiled and run in the browser, but the server "knows" about it and can invoke it.

```python
# This function is compiled to JS and runs in the User's Browser
@app.client.realtime
async def update_alert(message: str, color: str):
    from violetear.js import DOM

    # Update the DOM immediately
    el = DOM.find("status-message")
    el.text = message
    el.style(color=color)
```

### 2. Call it from the Server

Now the server code can call `update_alert.invoke(...)` for any specific client.
You can get the appropriate client ID via `@app.server.on("connect")` handlers.

You can also call it for all connected clients using `.broadcast()`. For example, to greet every client as it joins (the `connect` event fires per-client *after* startup, when there's a live socket to deliver to):

```python
# Fires once per client, right after their websocket comes up
@app.server.on("connect")
async def greet(client_id: str):
    await update_alert.invoke(
        client_id,
        message="Welcome!",
        color="green",
    )
```

> **Note:** Don't broadcast from `@app.server.on("startup")`. At startup the
> server has zero active websocket connections — clients only reconnect
> after startup completes — so any broadcast there silently no-ops.

### 3. Handle Connections

You can hook into WebSocket lifecycle events to track users or trigger actions when they join or leave.

```python
@app.server.on("connect")
async def on_join(client_id: str):
    print(f"Client {client_id} connected.")
    # You could broadcast a "User Joined" message here
    await update_alert.broadcast(f"User {client_id} joined!", "blue")

@app.server.on("disconnect")
async def on_leave(client_id: str):
    print(f"Client {client_id} left.")
```

Similarly, you can hook `@app.client.on("connect")` and `"disconnect"` events to execute client-side code whenever the client websocket connects and disconnects.

## 🌐 Shared State: Multiplayer in One Decorator

`@app.shared` makes collaborative features trivial. Decorate a `@dataclass` with `@app.shared` and every field assignment — from any client or from server code — automatically broadcasts to **all connected clients** and updates their DOM.

No manual broadcast calls. No `request_history`. No `receive_history`. No `@app.client.on("connect")` to request a state dump. Everything is automatic.

```python
from dataclasses import dataclass, field
from violetear import App
from violetear.js import Event

app = App(title="Shared Counter")

@app.shared
@dataclass
class Room:
    count: int = 0
    users: dict = field(default_factory=dict)
    # server_only=True → clients can read but cannot write
    version: str = field(default="1.0", metadata={"server_only": True})

@app.server.on("connect")
async def on_join(client_id: str):
    Room.users = {**Room.users, client_id: f"anon-{client_id[:6]}"}

@app.server.on("disconnect")
async def on_leave(client_id: str):
    users = dict(Room.users)
    users.pop(client_id, None)
    Room.users = users

@app.client.callback
async def on_click(event: Event):
    # Sends shared_set to server → server validates → broadcasts to ALL tabs
    Room.count = Room.count + 1
```

Open two browser tabs. Click the button in one. The counter updates in both — instantly, with zero extra wiring.

**How it works:** `Room` is a `SharedProxy` singleton on the server. Any field write intercepts `__setattr__`, which broadcasts a `shared_sync` WebSocket frame to every connection. On connect, the server pushes the full current state before the application's `on("connect")` handler fires. Client setters send `shared_set` to the server; the server is the source of truth and re-broadcasts to all clients (including the sender). The `server_only` metadata prevents clients from writing privileged fields.

## 📄 Partials & DOM Manipulation

`@app.partial` registers a GET route that returns a raw HTML fragment. The client fetches it and injects it into the page via `DOM.query(sel).load(url)`, which also re-hydrates any reactive bindings in the fragment.

```python
@app.partial("/messages")
def render_messages():
    ul = HTML.ul(id="msg-list")
    with ul as b:
        for msg in Room.messages:
            b.li(text=f"{msg['from']}: {msg['text']}")
    return ul

@app.client.callback
async def refresh(event: Event):
    DOM.find("msg-input").value = ""
    await post_message(text=DOM.find("msg-input").value)
    await DOM.query("#msg-area").load("/messages")
```

The full DOM manipulation API (available in `@app.client.*` functions via `from violetear.js import DOM`):

```python
DOM.find("id")              # getElementById → DOMElement
DOM.query("#sel")           # querySelector → DOMElement
DOM.query_all(".cls")       # querySelectorAll → list[DOMElement]

el.text = "hello"           # textContent
el.html = "<b>bold</b>"     # innerHTML (no re-hydration)
await el.load("/fragment")  # fetch + inject + re-hydrate

el.add_class("active")      # classList.add
el.remove_class("active")   # classList.remove
el.toggle_class("open")     # classList.toggle
el.has_class("active")      # classList.contains

el.attr("href", "/x")       # setAttribute
el.attr("href")             # getAttribute
el.remove_attr("disabled")  # removeAttribute

el.hide()                   # style.display = "none"
el.show()                   # style.display = ""
el.value                    # form field value (read/write)
el.clear()                  # innerHTML = ""
el.remove()                 # .remove()
el.focus() / el.blur()
el.scroll_into_view()
el.on("click", fn) / el.off("click", fn)
```

## 🛣️ Roadmap

The long-term vision for Violetear is to become a Python-native, full-stack, production-ready web framework. Here are some of the currently planned features:

  * [x] **📱 Progressive Web Apps (PWA)**: Simply pass `@app.route(..., pwa=True)` to automatically generate `manifest.json` and a Service Worker.
  * [x] **📡 Reverse RPC (Broadcast and Invoke)**: Invoke client-side functions from the server via websockets.
  * [ ] **🔥 JIT CSS**: An optimization engine that scans your Python code and serves *only* the CSS rules actually used by your components.
  * [ ] **🧭 SPA Engine**: An abstraction (`violetear.spa`) for building Single Page Applications.
  * [ ] **🔀 Client-Side Routing**: Define client-side routes that render specific components into a shell without reloading the page.
  * [x] **📃 Partial Views**: `@app.partial` returns raw HTML fragments; `DOM.query(sel).load(url)` fetches and injects them with automatic re-hydration.
  * [x] **🗃️ `@app.local`**: Reactive state that lives in the browser (per user). Changes update the DOM automatically.
  * [x] **🌐 `@app.shared`**: Real-time state that lives on the server (multiplayer). Changes are synced to all connected clients via **WebSockets**.

## 🤝 Contribution

`violetear` is open-source and we love contributions!

1.  Fork the repo.
2.  Install dependencies with `uv sync --extra server`.
3.  Run tests with `make` (or `make test-unit`).
4.  Submit a PR!

## 📄 License

MIT License. Copyright (c) Alejandro Piad.
