---
number: 2
title: "Feature Design: Progressive Web App (PWA) Support"
state: open
labels:
---

# Feature Design: PWA Integration

**Target Version:** v1.2
**Status:** Draft

This document outlines the design specifications for adding first-class Progressive Web App (PWA) support to the Violetear framework.

## Objective
Enable developers to turn their Violetear applications into installable software (Add to Homescreen) with offline capabilities by automatically generating and serving standard PWA assets (`manifest.json` and `sw.js`) and injecting the necessary HTML tags.

---

## 1. New Module: `violetear.pwa`

We will introduce a new module `violetear.pwa` to handle the generation of PWA assets. This keeps the core logic clean and makes PWA support strictly opt-in.

### 1.1 Data Structures

```python
@dataclass
class Icon:
    src: str
    sizes: str
    type: str = "image/png"
    purpose: str = "any maskable"
```

### 1.2 The `Manifest` Class

This class is responsible for generating the `manifest.json` file. It should support all standard Web App Manifest members.

```python
class Manifest:
    def __init__(
        self,
        name: str,
        short_name: str = None,
        start_url: str = ".",
        display: str = "standalone",
        background_color: str = "#ffffff",
        theme_color: str = "#ffffff",
        description: str = "",
        icons: List[Icon] = None
    ):
        # ... validation and storage ...

    def add_icon(self, src: str, sizes: str, type: str = "image/png"):
        # Helper to add icons fluently
        pass

    def render(self) -> str:
        # Returns the JSON string
        pass
```

### 1.3 The `ServiceWorker` Class

This class generates the `sw.js` logic. It needs to be smart about what to cache.

```python
class ServiceWorker:
    def __init__(self, cache_name: str = "violetear-v1"):
        self.cache_name = cache_name
        self.assets = set()

    def add_assets(self, *files: str):
        """Register files to be pre-cached during the 'install' phase."""
        self.assets.update(files)

    def render(self) -> str:
        """
        Generates the JavaScript code for the Service Worker.
        Should include:
        1. 'install' event: Opens cache and adds all self.assets.
        2. 'fetch' event: Network-first or Stale-while-revalidate strategy.
        """
        pass
```

## 2. Integration with `violetear.app.App`

The `App` class needs to act as the coordinator. It must serve the assets and inject the linkage into the HTML.

### 2.1 Configuration

We can add a PWA configuration step, or arguments to the `App` constructor.

```python
app = App(title="My App", pwa=True)
# Or for more control:
app.configure_pwa(
    manifest=Manifest(name="Full Name", theme_color="#333"),
    offline_support=True
)
```

### 2.2 Automatic Routing

If PWA is enabled, the `App` must automatically register routes for:

  * `GET /manifest.json` -\> Returns `app.pwa.manifest.render()`
  * `GET /sw.js` -\> Returns `app.pwa.service_worker.render()`

### 2.3 Asset Discovery

The `ServiceWorker` needs to know what to cache. The `App` class already knows about:

  * The Pyodide runtime URL (if client-side logic is used).
  * The generated Client Bundle (`/_violetear/bundle.py`).
  * Registered Stylesheets (via `app.add_style`).

The `App` should automatically populate the `ServiceWorker` asset list with these known resources.

### 2.4 HTML Injection

When rendering a `Document`, if PWA is enabled, the `App` must inject:

1.  **Manifest Link:**
    ```html
    <link rel="manifest" href="/manifest.json">
    ```
2.  **Meta Tags:**
    ```html
    <meta name="theme-color" content="...">
    <link rel="apple-touch-icon" href="...">
    ```
3.  **Registration Script:**
    ```html
    <script>
      if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
          navigator.serviceWorker.register('/sw.js');
        });
      }
    </script>
    ```

## 3. Task List

  - [ ] Create `violetear/pwa.py` with `Manifest` and `ServiceWorker` classes.
  - [ ] Update `App` to accept PWA configuration options.
  - [ ] Implement automatic route registration for `/manifest.json` and `/sw.js`.
  - [ ] Implement logic to auto-discover assets (styles, bundles) and add them to the Service Worker.
  - [ ] Update `App.render_document` (or the route wrapper) to inject the manifest link and SW registration script.