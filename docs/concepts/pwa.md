# Progressive Web Apps (PWA)

Any violetear route can become an installable PWA with a single parameter.

## Enable PWA

```python
from violetear.pwa import Manifest

app = App(title="My App", version="1.2.0")  # pin version for stable cache

@app.view("/", pwa=Manifest(
    name="My App",
    short_name="App",
    description="An amazing Python PWA",
    theme_color="#6b21a8",
))
def index():
    return Document(title="My App")
```

Or use the simple boolean form for defaults:

```python
@app.view("/", pwa=True)
def index():
    ...
```

## What it does

- Generates and serves `manifest.json` at `/_violetear/pwa/{hash}/manifest.json`
- Generates and serves a Service Worker at `/_violetear/pwa/{hash}/sw.js`
- Injects the manifest `<link>` and SW registration script into the document

## Caching strategy

| Resource | Strategy |
|----------|----------|
| HTML navigation | Network-first (falls back to cache offline) |
| JS/CSS assets | Cache-first (versioned — updates on version bump) |

## Multiple PWAs

Different routes can be independent PWAs:

```python
@app.view("/app1", pwa=Manifest(name="App 1", ...))
def app1(): ...

@app.view("/app2", pwa=Manifest(name="App 2", ...))
def app2(): ...
```

## Limitations

- Push notifications: not supported
- Background sync for offline form submissions: not supported (handle manually)
