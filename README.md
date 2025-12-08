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

Use it for anything: from a simple script to generate a CSS file, to a static site generator, all the way up to a full-stack Isomorphic Web App powered by **FastAPI** and **Pyodide**.

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

First, we create the application instance. This wraps FastAPI to provide a powerful server engine.

```python
from violetear import App, StyleSheet
from violetear.markup import Document, Element
from violetear.color import Colors
from violetear.style import Style
from violetear.dom import Event

app = App(title="Violetear Counter")
```

### 2. Define Styles (CSS-in-Python)

Instead of writing CSS strings, use the fluent API to define your theme.

```python
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

Define a function that runs on the server. The `@app.server` decorator exposes this function so your client code can call it directly.

```python
@app.server
async def report_count(current_count: int, action: str):
    """
    This runs on the SERVER.
    FastAPI automatically validates that current_count is an int.
    """
    print(f"[SERVER] Count is now {current_count} (Action: {action})")
    return {"status": "received"}
```

### 4. Client Logic (In-Browser Python)

Define the interactivity. We use `@app.startup` to restore state when the page loads.

```python
@app.startup
async def init_counter():
    """
    Runs automatically when the page loads (Client-Side).
    Restores the counter from Local Storage so F5 doesn't reset it.
    """
    from violetear.dom import Document
    from violetear.storage import store

    # We can access storage like an object!
    saved_count = store.count
    if saved_count is not None:
        Document.find("display").text = str(saved_count)
        print(f"Restored count: {saved_count}")
```

And we use `@app.client` to handle user interactions and run Python code in the browser. Check out the Pythonic API for interacting with the DOM and the LocalStorage. We can also call server-side functions seamlessly, via automagic RPC (Remote Procedure Call).

```python
@app.client
async def handle_change(event: Event):
    """
    Runs in the browser on click.
    """
    from violetear.dom import Document
    from violetear.storage import store

    # A. Get current state from DOM
    display = Document.find("display")
    # We can read/write text content directly
    current_value = int(display.text)

    # B. Determine action
    action = event.target.id  # "plus" or "minus"
    new_value = current_value + (1 if action == "plus" else -1)

    # C. Update DOM immediately (Responsive)
    display.text = str(new_value)

    # D. Save to Local Storage (Persistence)
    # This automatically serializes the value to JSON
    store.count = new_value

    # E. Sync with Server (Background)
    await report_count(current_count=new_value, action=action)
```

### 5. The UI (Server-Side Rendered)

Finally, create the route that renders the initial HTML. We attach the style and bind the Python function to the button's click event.

```python
@app.route("/")
def index():
    doc = Document(title="Violetear Counter")

    # Auto-serve our generated CSS at this URL
    doc.style(style, href="/style.css")

    doc.body.add(
        Element("div", classes="counter-card").extend(
            Element("h2", text="Isomorphic Counter"),

            # The Count
            Element("div", id="display", classes="count-display", text="0"),

            # Controls - Both call the same Python function
            Element("button", id="minus", text="-", classes="btn-minus btn").on(
                "click", handle_change
            ),
            Element("button", id="plus", text="+", classes="btn-plus btn").on(
                "click", handle_change
            ),

            Element("p", text="Refresh the page! The count persists.").style(
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
  * **Pythonic DOM**: A wrapper (`violetear.dom`) that provides a clean, type-safe Python API for DOM manipulation in the browser.
  * **Smart Storage**: A Pythonic wrapper (`violetear.storage`) around `localStorage` that handles JSON serialization automatically and allows attribute access (`store.user.name`).
  * **Asset Management**: Stylesheets created in Python are served directly from memory.
  * **Seamless RPC**: Call server functions from the browser as if they were local.

## 📱 Progressive Web App (PWA) Support

Violetear allows you to turn any route into an installable PWA. This enables your app to:

1.  **Be Installed:** Users can add it to their home screen (mobile/desktop).
2.  **Work Offline:** The app shell and assets are cached automatically.
3.  **Auto-Update:** Changes to your Python code are detected, ensuring users always see the latest version.

### How to Enable PWA

Simply pass `pwa=True` (or a `Manifest` object) to the `@app.route` decorator.

**Important:** You must define an app `version`. If you don't, Violetear generates a random one on every restart, which will force users to re-download the app every time you deploy.

```python
from violetear import App, Manifest

# 1. Set a version string (e.g., from git commit or semantic version)
app = App(title="My App", version="v1.0.2")

# 2. Enable PWA on your main route
@app.route("/", pwa=Manifest(
    name="My Super App",
    short_name="SuperApp",
    description="An amazing Python PWA",
    theme_color="#6b21a8"
))
def home():
    return Document(...)
```

### Caching Strategy

Violetear uses a hybrid strategy to ensure safety and speed:

  * **Navigation (HTML):** *Network-First*. It tries to fetch the latest version from the server. If offline, it falls back to the cache.
  * **Assets (JS/CSS):** *Cache-First*. Assets are versioned (e.g., `bundle.py?v=1.0.2`). This ensures instant loading while guaranteeing updates when the version changes.

### Current Limitations

  * **Push Notifications:** Not yet supported (requires VAPID key generation and a push server).
  * **Background Sync:** Offline actions (like submitting a form while disconnected) are not automatically retried when online. You must handle connection errors manually in your client logic.

## 🛣️ Roadmap

We are currently in v1.1 (Core). Here is the vision for the immediate future of Violetear:

### v1.2: The "App" Update (Deployment)

  * [x] **📱 Progressive Web Apps (PWA)**: Simply pass `@app.route(..., pwa=True)` to automatically generate `manifest.json` and a Service Worker.
  * [ ] **🔥 JIT CSS**: An optimization engine that scans your Python code and serves *only* the CSS rules actually used by your components.

### v1.3: The "Navigation" Update (SPA)

  * [ ] **🧭 SPA Engine**: An abstraction (`violetear.spa`) for building Single Page Applications.
  * [ ] **Client-Side Routing**: Define routes that render specific components into a shell without reloading the page.

### v1.4: The "Twin-State" Update (Reactivity)

  * [ ] **`@app.local`**: Reactive state that lives in the browser (per user). Changes update the DOM automatically.
  * [ ] **`@app.shared`**: Real-time state that lives on the server (multiplayer). Changes are synced to all connected clients via **WebSockets**.

## 🤝 Contribution

`violetear` is open-source and we love contributions!

1.  Fork the repo.
2.  Install dependencies with `uv sync`.
3.  Run tests with `make test`.
4.  Submit a PR!

## 📄 License

MIT License. Copyright (c) Alejandro Piad.
