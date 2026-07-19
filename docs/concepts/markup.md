# Markup

violetear's markup layer builds HTML trees programmatically with a fluent Python API.

## Document

```python
from violetear.markup import Document

doc = Document(title="My Page")
doc.head.link_css("/style.css")
doc.head.add_script(src="/app.js")
```

## Building elements

Use the `with elem as builder:` context manager to attach children:

```python
with doc.body as body:
    with body.div(classes="container") as c:
        c.h1(text="Hello, world!")
        c.p(text="Built with violetear.")
        c.button(text="Click me").onclick(handle_click)
```

Or pass children directly to the constructor:

```python
from violetear.markup import HTML

card = HTML.div(
    HTML.h2(text="Title"),
    HTML.p(text="Body text"),
    classes="card",
    id="my-card",
)
```

## Common elements

All standard HTML tags are available:

```python
body.div()
body.section()
body.h1() / h2() / h3() / h4()
body.p()
body.span()
body.a(href="/path", text="Link")
body.img(src="/img.png", alt="…")
body.ul() / ol() / li()
body.table() / thead() / tbody() / tr() / th() / td()
body.form(action="/submit", method="post")
body.input(type="text", id="name", placeholder="…")
body.button(text="Submit")
body.label(text="Name:", for_="name")
```

## Event binding

```python
btn.on("click", handle_click)    # generic
btn.onclick(handle_click)        # shorthand
```

The function name is serialized as a `data-on-click` attribute at render time and bound to the actual compiled JS function by the runtime.

## Reactive binding

Bind an element's content to a state field:

```python
with body.div() as display:
    display.text(State.count)   # renders data-bind-text="State.count"
```

When `State.count` changes in the browser, the element updates automatically.

## Rendering

```python
html_string = doc.render()      # full HTML document
fragment = HTML.div(...).render()  # fragment (for @app.partial)
```
