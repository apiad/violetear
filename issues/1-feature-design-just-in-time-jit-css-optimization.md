---
number: 1
title: "Feature Design: Just-In-Time (JIT) CSS Optimization"
state: open
labels:
---

# Feature Design: JIT CSS Optimization

**Target Version:** v1.2
**Status:** Draft

This document outlines the design specifications for adding an automatic CSS optimization engine to Violetear. This feature ensures that Server-Side Rendered (SSR) pages serve the absolute minimum amount of CSS required to render the content, significantly improving First Contentful Paint (FCP) and reducing network usage.

## Objective
Implement a pipeline that scans the generated HTML (Document object model), identifies the CSS classes actually in use, and generates a minimal CSS subset on the fly to be inlined directly into the response.

## 1. Scanner Logic (`violetear.markup`)

We need a reliable way to traverse the Violetear component tree and extract all class names referenced by the elements.

### 1.1 `Element.scan_classes()`

* **Responsibility**: Recursively collect all tokens in `self.classes` from the element and all its children.
* **Returns**: `Set[str]` to ensure uniqueness.

*(Note: Basic implementation already exists in the current codebase, but needs to be formalized and tested against `Component` subclasses).*

### 1.2 `Document.get_used_classes()`

* **Responsibility**: Entry point for the App to request the usage set from the entire document body.

## 2. Filter Logic (`violetear.stylesheet`)

The `StyleSheet` class needs a new rendering mode that accepts a filter.

### 2.1 `StyleSheet.render_subset(used_classes: Set[str]) -> str`

* **Input**: A set of class names (strings) found in the document.
* **Logic**:
    1.  Iterate over all stored `Style` objects.
    2.  Check the `Selector` of each style.
    3.  **Inclusion Criteria**:
        * If the selector targets a **Tag** (e.g., `body`, `h1`), always include (global styles).
        * If the selector targets an **ID** (e.g., `#header`), always include (specific styles).
        * If the selector targets **Classes** (e.g., `.btn.primary`):
            * Include ONLY if **all** classes in the selector are present in `used_classes`.
            * Example: Rule `.btn.primary` is kept only if both `btn` and `primary` are used.
    4.  **Animations**: If a style is included and it uses an `@keyframes` animation, that animation definition must also be included in the output.
* **Output**: A string containing only the valid CSS rules.

## 3. Server-Side Integration (`violetear.app.App`)

The `App` class handles the request/response lifecycle and decides *how* to serve the CSS.

### 3.1 Routing Logic Update

We will update the `route` wrapper to support a mode switch (e.g., `jit=True` or default behavior for non-PWA routes).

**Workflow:**
1.  Execute user view function -> Get `Document`.
2.  **Scan**: Call `doc.get_used_classes()` to get the set of active tokens.
3.  **Process Assets**: Iterate through `doc.head.styles`.
    * If the resource is a `StyleSheet` object (not a string URL):
        * Call `sheet.render_subset(used_classes)`.
        * Replace the `<link>` tag in the header with a `<style>` tag containing the optimized CSS string.
    * If the resource is a URL (CDN/Static file):
        * Leave as is (cannot optimize external resources).
4.  **Return**: Send the optimized HTML response.

### 3.2 Caching Considerations (Future)

* For high-traffic production, we might want to cache the generated CSS string based on a hash of the `used_classes` set to avoid re-filtering the stylesheet on every request.

## 4. Usage Example

No changes required in user code! The optimization happens transparently.

```python
# User defines a massive theme (e.g. Atomic/Tailwind preset with 10,000 rules)
app.add_style(Atomic())

@app.route("/")
def home():
    # User uses only 2 classes
    return Document().add(Element("div", classes="text-xl text-red"))

# RESULT:
# The browser receives an HTML with a <style> block containing
# ONLY the rules for .text-xl and .text-red.
# The other 9,998 rules are discarded.
```

## 5. Task List

  - [ ] Add `render_subset` method to `StyleSheet`.
  - [ ] Ensure `render_subset` correctly handles dependency resolution (e.g., styles using `@keyframes`).
  - [ ] Update `App.route` to perform the scan-and-inline process for `Document` responses.
  - [ ] Add unit tests verifying that unused classes are indeed stripped from the output.