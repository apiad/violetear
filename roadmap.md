# Violetear v1.0 - The Full-Stack Python Framework

**Status:** Draft
**Target:** v1.0 (Evolution from Library to Framework)

## Summary
Transform `violetear` into a hybrid, full-stack Python web framework. It will support both **Server-Side Rendering (SSR)** for high-performance static content and **Client-Side Rendering (CSR)** via Pyodide for rich interactivity. The architecture remains modular: the core library stays zero-dependency, while the framework layer (`violetear.app`) leverages `FastAPI` and standard WebAssembly tools.

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

- [ ] **Manifest Generator**: Create a class to generate `manifest.json` from `App` metadata.
- [ ] **Route Configuration**: Add `pwa=True` parameter to `@app.route`.
    - Serves the manifest linked to that specific scope.
    - Injects `<meta>` tags for theme color and icons.
- [ ] **Service Worker**: Implement a default Service Worker generator.
    - Automatically cache the Pyodide runtime and the app's registered CSS/JS assets (from the Asset Registry).
