# 🐦 violetear

**The Full-Stack Web Framework for Pythonistas.**

<!-- Project badges -->
![PyPI - Version](https://img.shields.io/pypi/v/violetear)
![PyPi - Python Version](https://img.shields.io/pypi/pyversions/violetear)
![PyPi - Downloads (Monthly)](https://img.shields.io/pypi/dm/violetear)
![Github - Commits](https://img.shields.io/github/commit-activity/m/apiad/violetear)


`violetear` is a minimalistic yet fully capable framework for building modern web applications in **pure Python**. It eliminates the context switch between backend and frontend by allowing you to write your styles, your markup, and your client-side logic all in the language you love.

It features a unique 3-layer architecture:

1.  **🎨 Styling Layer**: Generate CSS rules programmatically with a fluent, pythonic API. No more huge `.css` files; just composable Python objects.
2.  **🧱 UI Layer**: Build reusable HTML components with a fluent builder pattern. Type-safe, refactor-friendly, and composable.
3.  **⚡ Logic Layer**: Write server-side and client-side code in the same file. `violetear` handles the compilation, bundling, and RPC bridges for you seamlessly.

Use it for anything: from a simple script to generate a CSS file, to a static site generator, all the way up to a full-stack Isomorphic Web App powered by **FastAPI** and **Pyodide**.

## 📦 Installation

To use the core library (HTML/CSS generation only), install the base package:

```bash
pip install violetear
```

To build full-stack applications (with the App Engine and Server), install the server extras:

```bash
pip install "violetear[server]"
```

## 🚀 Quickstart: The Isomorphic Counter

Let's build a fully interactive "Counter" app where the state updates instantly in the browser using our Pythonic DOM API, but every change is reported back to the server. **Zero JavaScript required.**

### Step 1: Initialize the App

First, we create the application instance. This wraps FastAPI to provide a powerful server engine.

```python
from violetear import App, StyleSheet
from violetear.markup import Document, Element
from violetear.color import Colors
from violetear.style import Style
from violetear.dom import Event

app = App(title="Violetear Counter")
```

### Step 2: Define Styles (CSS-in-Python)

Instead of writing CSS strings, use the fluent API to define your theme.

```python
# Create a global stylesheet
style = StyleSheet()

style.select("body").background(Colors.AliceBlue).font(family="sans-serif").flexbox(
    align="center", justify="center"
).height("320px").margin(top=20)

style.select(".counter-card").background(Colors.White).padding(40).rounded(15).shadow(
    blur=20, color="rgba(0,0,0,0.1)"
).text(align="center")

style.select(".count-display").font(size=64, weight="bold").color(
    Colors.SlateBlue
).margin(10)

style.select("button").padding("10px 20px").font(size=20, weight="bold").margin(
    5
).rounded(8).border(0).rule("cursor", "pointer").color(Colors.White)

style.select(".btn-plus").background(Colors.MediumSeaGreen)
style.select(".btn-minus").background(Colors.IndianRed)
style.select(".btn:hover").rule("opacity", "0.8")
```

### Step 3: Server Logic (RPC)

Define a function that runs on the server. The `@app.server` decorator exposes this function so your client code can call it directly.

```python
@app.server
async def report_count(current_count: int, action: str):
    """
    This runs on the server.
    FastAPI automatically validates that current_count is an int.
    """
    print(f"[SERVER] Count is now {current_count} (Action: {action})")
    return {"status": "received"}
```

### Step 4: Client Logic (In-Browser Python)

Define the interactivity. The `@app.client` decorator compiles this function and sends it to the browser to run inside Pyodide. We use `violetear.dom` to manipulate the page using a familiar, pythonic API.

```python
@app.client
async def handle_change(event: Event):
    """
    Runs in the browser.
    """
    # Import the DOM wrapper (Client-Side implementation)
    from violetear.dom import Document

    # A. Get current state from DOM
    display = Document.find("display")
    current_value = int(display.text)

    # B. Determine action
    action = event.target.id  # "plus" or "minus"
    new_value = current_value + (1 if action == "plus" else -1)

    # C. Update DOM immediately (Responsive)
    display.text = str(new_value)

    # D. Sync with Server (Background)
    # This calls the @app.server function seamlessly!
    await report_count(current_count=new_value, action=action)
```

### Step 5: The UI (Server-Side Rendering)

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

            Element("p", text="Check server console for pings.").style(
                Style().color(Colors.Gray).margin(top=20)
            ),
        )
    )

    return doc

if __name__ == "__main__":
    app.run(port=8000)
```

Run it with `python main.py` and open `http://localhost:8000`. You have a full-stack, styled, interactive app in just 60 lines of pure Python!

## ✨ Features

### 🎨 Powerful Styling Engine

  * **Fluent API**: `style.select("div").color(Colors.Red).margin(10)`
  * **Type-Safe Colors**: Built-in support for RGB, HSL, Hex, and a massive library of standard web colors (`violetear.color.Colors`).
  * **Unit Handling**: Intelligent handling of `px`, `rem`, `em`, `vh`, etc.
  * **Presets**:
      * `FlexGrid`: Create complex 12-column layouts with a single line.
      * `SemanticDesign`: Pre-configured design systems for typography and buttons.
      * `UtilitySystem`: Generate thousands of utility classes (`p-4`, `text-xl`, `flex`, `hover:bg-red-500`) purely in Python without any build step.
      * `Atomic`: A pre-made, completely configurable, Tailwind-like atomic CSS based on the utility system.

### 🧱 Component System

  * **Declarative Builder**: Create HTML structures without writing HTML strings.
  * **Reusability**: Subclass `Component` to create reusable widgets (Navbars, Cards, Modals) that encapsulate their own structure and logic.
  * **Context-Aware**: Elements know about their parents and styles.

### ⚡ Full-Stack Application Engine

  * **Hybrid Architecture**: Supports both **Server-Side Rendering (SSR)** for SEO and speed, and **Client-Side Rendering (CSR)** for interactivity.
  * **Pythonic DOM**: A wrapper (`violetear.dom`) that provides a clean, type-safe Python API for DOM manipulation in the browser (`Document.find("id").text("Hello")`).
  * **Smart Hydration**: If a page has no interactive elements, `violetear` serves pure HTML. If you add an `@app.client` handler, it automatically injects the runtime.
  * **Asset Management**: Stylesheets created in Python are served directly from memory; no need to manage static files manually.
  * **Seamless RPC**: Call server functions from the browser as if they were local. Arguments and return values are automatically serialized.

## 🛣️ Roadmap

We are just getting started. Here is what's coming in v1.1 and beyond:

  * **📱 Progressive Web Apps (PWA)**: Simply pass `App(pwa=True)` to automatically generate `manifest.json` and a Service Worker, making your Python app installable and offline-capable.
  * **🔥 JIT CSS**: An optimization engine that scans your Python code and serves *only* the CSS rules actually used by your components, reducing file size to the minimum.

## 🤝 Contribution

`violetear` is open-source and we love contributions!

1.  Fork the repo.
2.  Install dependencies with `uv sync`.
3.  Run tests with `make test`.
4.  Submit a PR!

## 📄 License

MIT License. Copyright (c) Alejandro Piad.
