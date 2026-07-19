# Partials & DOM Manipulation

violetear v1.5 adds two tightly coupled features:

- **`@app.partial(path)`** — a server route that returns a raw HTML fragment (not a full Document). Clients fetch it and inject it into the page.
- **`DOM` API** — a fluent, OOP DOM manipulation API compiled to JavaScript. `DOM.find(id)` and `DOM.query(selector)` return a `DOMElement` wrapper whose `.load(url)` is the entry point for partials.

## @app.partial

```python
from violetear.markup import HTML

@app.partial("/chat/messages")
def render_messages():
    ul = HTML.ul(id="msg-list")
    with ul as b:
        for msg in Room.messages:
            b.li(text=f"{msg['from']}: {msg['text']}")
    return ul
```

- The decorated function returns any `Element` (from `violetear.markup`).
- `@app.partial` registers a FastAPI `GET` route that calls the function and returns `HTMLResponse(element.render())`.
- The response is a raw HTML fragment — no `<html>`/`<head>`/`<body>` wrapper, no JS bundle.
- Styles must come from the main page's stylesheet (partials share the page's CSS).

## DOM manipulation API

Import from `violetear.js` for IDE/mypy support; these become JS globals in the browser:

```python
from violetear.js import DOM
```

### Accessing elements

```python
el = DOM.find("my-id")           # getElementById → DOMElement
el = DOM.query("#msg-area")      # querySelector → DOMElement (first match)
els = DOM.query_all(".card")     # querySelectorAll → list[DOMElement]
```

### Loading a partial

```python
await DOM.query("#msg-area").load("/chat/messages")
# 1. GET /chat/messages
# 2. Inject response as innerHTML of #msg-area
# 3. Re-hydrate reactive bindings in the new subtree
```

Any `data-bind-*` attributes in the injected HTML are automatically registered with `ReactiveRegistry` and will update when shared state changes.

### Full DOMElement API

**Content**

| Method | JS equivalent |
|--------|--------------|
| `el.text = "…"` | `el.textContent = "…"` |
| `el.html("…")` | `el.innerHTML = "…"` (no re-hydration) |
| `await el.load(url)` | fetch + inject + re-hydrate |

**Classes**

| Method | JS equivalent |
|--------|--------------|
| `el.add_class("a", "b")` | `classList.add(…)` |
| `el.remove_class("a")` | `classList.remove(…)` |
| `el.toggle_class("active")` | `classList.toggle(…)` |
| `el.has_class("active")` | `classList.contains(…)` |

**Attributes**

| Method | JS equivalent |
|--------|--------------|
| `el.attr("href", "/x")` | `setAttribute("href", "/x")` |
| `el.attr("href")` | `getAttribute("href")` |
| `el.remove_attr("disabled")` | `removeAttribute("disabled")` |

**Visibility**

| Method | JS equivalent |
|--------|--------------|
| `el.hide()` | `style.display = "none"` |
| `el.show()` | `style.display = ""` |
| `el.show("flex")` | `style.display = "flex"` |

**Form values**

| Method | JS equivalent |
|--------|--------------|
| `el.value` | `el.value` (read) |
| `el.value = "…"` | `el.value = "…"` |

**Structure**

| Method | JS equivalent |
|--------|--------------|
| `el.clear()` | `innerHTML = ""` |
| `el.remove()` | `.remove()` |

**Focus / scroll**

| Method | JS equivalent |
|--------|--------------|
| `el.focus()` | `.focus()` |
| `el.blur()` | `.blur()` |
| `el.scroll_into_view()` | `.scrollIntoView({behavior: "smooth"})` |

**Events**

| Method | JS equivalent |
|--------|--------------|
| `el.on("click", fn)` | `addEventListener("click", fn)` |
| `el.off("click", fn)` | `removeEventListener("click", fn)` |

## Example — chat message list

```python
@app.partial("/chat/messages")
def render_messages():
    ul = HTML.ul(id="msg-list")
    with ul as b:
        for msg in Room.messages:
            b.li(text=f"{msg['from']}: {msg['text']}")
    return ul

@app.client.callback
async def send_msg(event: Event):
    from violetear.js import DOM
    text = DOM.find("msg-input").value
    if not text:
        return
    DOM.find("msg-input").value = ""
    await post_message(name="Me", text=text)
    await DOM.query("#msg-area").load("/chat/messages")

@app.server.rpc
async def post_message(name: str, text: str):
    Room.messages.append({"from": name, "text": text})
```

See [examples/07_partial.py](https://github.com/apiad/violetear/blob/main/examples/07_partial.py) for the full runnable example.

## Re-hydration

When `.load(url)` injects a partial, `_hydrate_subtree(root, scope)` runs on the injected subtree:

1. **Event bindings** — `data-on-*` attributes are bound to scope functions.
2. **Reactive bindings** — `data-bind-*` attributes are registered with `ReactiveRegistry`.
3. **Flush** — `ReactiveRegistry.flush_subtree(root)` immediately applies cached reactive values so the partial reflects current state.

This means partials that contain `data-bind-*` bindings (e.g. from `@app.local` state) update reactively going forward.

## What's out of scope (v1)

- `el.append(child_element)` — client-side element construction
- Partial streaming (chunked transfer)
- `query_all` iteration helpers
- Cache headers on partial responses
- Stale-binding cleanup on replace (detached nodes are no-ops; GC handles memory)
