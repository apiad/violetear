---
number: 3
title: "Feature Design: Single Page Application (SPA) Engine"
state: open
labels:
---

# Feature Design: SPA Engine

**Target Version:** v1.3
**Status:** Draft

This document outlines the design specifications for adding a first-class Single Page Application (SPA) engine to Violetear. This allows building multi-view applications where navigation is handled instantly in the browser without page reloads, while maintaining full Server-Side Rendering (SSR) capability for the initial load.

## Objective
Provide a Pythonic abstraction for defining client-side routes, views, and navigation logic. The framework should handle the complexity of the History API, DOM reconciliation, and deep-linking support automatically.

## 1. New Module: `violetear.spa`

We will introduce `violetear.spa` to contain the shell and routing logic.

### 1.1 The `SPA` Class (The Shell)

Inherits from `Document`. It acts as the container for the entire application.

```python
class SPA(Document):
    def __init__(self, title: str, base_url: str = "/"):
        super().__init__(title=title)
        self.routes = {}  # Map[path, Component]
        self.base_url = base_url

    def page(self, path: str, component: Callable[[], Element]):
        """Registers a view for a specific route."""
        self.routes[path] = component
        return self

    def render(self, initial_path: str = "/") -> str:
        """
        Renders the Shell.

        Logic:
        1. Iterate through all registered pages.
        2. Render each one into a container <div id="page-{hash}">.
        3. Set 'display: block' ONLY for the page matching 'initial_path'.
        4. Set 'display: none' for all others.
        5. Inject the client-side router script.
        """
        pass
```

### 1.2 The `Link` Component

A helper to create navigation links that hook into the client-side router instead of triggering a browser refresh.

```python
class Link(Element):
    def __init__(self, text: str, to: str, **kwargs):
        super().__init__("a", text=text, href=to, **kwargs)
        # Mark it so the Router knows to intercept the click
        self.attrs(data_spa_link="true")
```

## 2. Client-Side Runtime (`violetear/spa_client.py`)

This Python module will be bundled into the client (injected by `App`). It manages the browser state.

### 2.1 The `Router` Class

```python
class Router:
    def __init__(self, route_map: dict):
        self.routes = route_map # Map[path, div_id]

        # Listen for Back/Forward buttons
        window.addEventListener("popstate", self.handle_popstate)

        # Listen for Link clicks (Event Delegation)
        document.body.addEventListener("click", self.handle_link_click)

    def navigate(self, path: str):
        """
        1. Update window.history.pushState(path).
        2. Call self.render(path).
        """
        pass

    def render(self, path: str):
        """
        1. Find the target div ID for this path.
        2. Hide all other page divs.
        3. Show target div.
        """
        pass
```

## 3. Server-Side Integration (`violetear.app.App`)

We need a way to serve the SPA shell regardless of which sub-route the user requests (Deep Linking support).

### 3.1 `spa_route` Decorator

```python
    def spa_route(self, path: str):
        """
        Registers a catch-all route for an SPA.
        Example: @app.spa_route("/dashboard/{path:path}")
        """
        def decorator(func):
            # 1. Register route with FastAPI (catch-all)
            # 2. When called, pass 'path' to the user function
            # 3. Expect user function to return an SPA instance
            # 4. Call spa.render(initial_path=path) to ensure correct SSR state
            pass
        return decorator
```

## 4. Usage Example

```python
dashboard = SPA(title="Admin Panel", base_url="/admin")

# Define Views
def Home():
    return Element("div").add(
        Element("h1", text="Dashboard"),
        Link(text="Settings", to="/admin/settings")
    )

def Settings():
    return Element("div").add(
        Element("h1", text="Settings"),
        Link(text="Back", to="/admin")
    )

# Register Views
dashboard.page("/", Home)
dashboard.page("/settings", Settings)

# Server Mount
@app.spa_route("/admin/{path:path}")
def serve_dashboard(request, path: str):
    return dashboard
```

## 5. Task List

  - [ ] Create `violetear.spa` module with `SPA` and `Link` classes.
  - [ ] Implement `violetear/spa_client.py` (Client-side Router logic using `violetear.dom`).
  - [ ] Add `spa_route` method to `App` class for catch-all routing.
  - [ ] Update `App._generate_bundle` to include the `spa_client` module if an SPA is detected.