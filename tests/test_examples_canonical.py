"""
Thin smoke tests for the canonical examples in `examples/0N_*.py`.

Each test verifies that the example module loads, builds, and produces
output with the expected shape. The goal is to catch regressions when
the framework changes — not to validate the examples' behavior in depth.

See `issues/6-canonical-examples-design.md` for the design.
"""

import ast
import hashlib
import importlib.util
import sys
from pathlib import Path

# Top-level `await` is legal in the violetear bundle because Pyodide runs it via
# `pyodide.runPythonAsync(...)`. Standard `compile()` needs this flag to accept it.
COMPILE_ASYNC = ast.PyCF_ALLOW_TOP_LEVEL_AWAIT

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def _load(filename: str):
    """Import an example module by filename and register it in sys.modules.

    Registration is REQUIRED because violetear's bundle generator calls
    `inspect.getsource(cls)` on `@app.local` state classes; without a sys.modules
    entry, that raises `TypeError: <class is a built-in class>` (see gap 7.5).
    """
    name = filename.removesuffix(".py")
    spec = importlib.util.spec_from_file_location(name, EXAMPLES_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# -- 01_static -----------------------------------------------------------------


def test_01_static_renders_html_and_css(tmp_path):
    """Tier 1: pure-markup example writes a valid HTML + CSS pair to disk."""
    mod = _load("01_static.py")

    html_path, css_path = mod.write_to(tmp_path)

    assert html_path.exists()
    assert css_path.exists()

    html = html_path.read_text()
    css = css_path.read_text()

    # HTML shape
    assert html.lstrip().startswith("<!DOCTYPE html>")
    assert "<title>violetear · Design Tokens</title>" in html
    assert 'class="page-title"' in html
    assert 'class="swatch"' in html
    # Inline swatch chip style proves a Color rendered into the doc
    assert "background-color: rgba(" in html

    # CSS shape: normalize preamble + at least one of our class selectors
    assert "modern-normalize" in css
    assert ".swatch-chip" in css
    assert ".tokens-heading" in css


# -- 02_ssr --------------------------------------------------------------------


def test_02_ssr_guestbook_round_trips_an_entry():
    """Tier 2: GET shows form + empty state; POST appends + redirects; subsequent GET shows the entry."""
    from fastapi.testclient import TestClient

    mod = _load("02_ssr.py")
    # Reset the in-memory store between test runs in case other tests touched it.
    mod.entries.clear()

    client = TestClient(mod.app.api)

    # Empty state
    r = client.get("/")
    assert r.status_code == 200
    assert "No entries yet" in r.text
    assert "<form" in r.text and 'method="post"' in r.text
    # Confirm the for_= leak fix held — no underscore-suffixed attrs in output.
    assert "for_=" not in r.text

    # Served stylesheet route
    r = client.get("/style.css")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/css")
    assert ".entry-name" in r.text

    # POST and follow redirect
    r = client.post(
        "/entries",
        data={"name": "Alex", "message": "hello"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/"

    # Entry now visible
    r = client.get("/")
    assert "Alex" in r.text
    assert "hello" in r.text
    assert "No entries yet" not in r.text

    # Pydantic-ish enforcement: missing field is rejected by FastAPI Form(...)
    r = client.post("/entries", data={"name": "Alex"})
    assert r.status_code == 422


# -- 03_interactive ------------------------------------------------------------


def test_03_interactive_ssr_bindings_and_rpc_and_bundle():
    """Tier 3: SSR emits data-bind-value for each input; RPC returns precise
    conversion; bundle compiles (the canary for the inspect.getsource issue)."""
    from fastapi.testclient import TestClient

    mod = _load("03_interactive.py")
    client = TestClient(mod.app.api)

    # SSR markup — reactive bindings on each input
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    assert 'data-bind-value="UiState.meters"' in html
    assert 'data-bind-value="UiState.feet"' in html
    assert 'data-bind-value="UiState.inches"' in html
    # Mode footer is bound via .text()
    assert 'data-bind-text="UiState.mode"' in html
    # Event-listener attrs from .on("input", callback)
    assert 'data-on-input="on_meters_change"' in html
    assert 'data-on-change="on_mode_change"' in html

    # Served stylesheet
    r = client.get("/style.css")
    assert r.status_code == 200
    assert ".field-input" in r.text

    # RPC endpoint — happy path returns precise conversion
    r = client.post("/_violetear/rpc/precise_convert", json={"meters": 2.0})
    assert r.status_code == 200
    body = r.json()
    assert abs(body["feet"] - 2.0 * 3.28083989501) < 1e-9
    assert abs(body["inches"] - 2.0 * 39.3700787402) < 1e-9

    # Bundle compiles — proves the @app.local state class and all client
    # functions got transpiled without inspect.getsource blowing up.
    r = client.get("/_violetear/bundle.py")
    assert r.status_code == 200
    compile(r.text, "<bundle-03>", "exec", flags=COMPILE_ASYNC)


# -- 04_pwa --------------------------------------------------------------------


def test_04_pwa_manifest_serviceworker_and_bundle():
    """Tier 4: SSR markup carries reactive bindings + a `data-mode` button trio,
    the per-route manifest endpoint serves the expected JSON, the Service
    Worker script lists the bundle URL in its asset cache, and the bundle
    compiles."""
    from fastapi.testclient import TestClient

    mod = _load("04_pwa.py")
    client = TestClient(mod.app.api)

    # SSR markup — reactive bindings on the time display, mode label, sessions
    # counter; mode buttons carry `data-mode` (not `data_mode` — gap 7.4).
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    assert 'data-bind-text="PomodoroState.time_display"' in html
    assert 'data-bind-text="PomodoroState.mode"' in html
    assert 'data-bind-text="PomodoroState.sessions"' in html
    assert 'data-on-click="start"' in html
    assert 'data-on-click="pause"' in html
    assert 'data-on-click="reset"' in html
    assert 'data-on-click="switch_mode"' in html
    assert 'data-mode="work"' in html
    assert 'data-mode="short"' in html
    assert 'data-mode="long"' in html
    # Initial render shows the default work duration.
    assert "25:00" in html
    # PWA glue: manifest link + SW registration injected into the page.
    assert "/manifest.json" in html
    assert "/sw.js" in html

    # Manifest endpoint — JSON with the values we passed to Manifest(...).
    scope_hash = hashlib.md5(b"/").hexdigest()[:8]
    r = client.get(f"/_violetear/pwa/{scope_hash}/manifest.json")
    assert r.status_code == 200
    manifest = r.json()
    assert manifest["name"] == "Pomodoro"
    assert manifest["short_name"] == "🍅"
    assert manifest["theme_color"] == "#dc2626"
    assert manifest["display"] == "standalone"
    # _register_pwa rewrites start_url + scope to the view's path.
    assert manifest["scope"] == "/"
    assert manifest["start_url"] == "/"

    # Service Worker endpoint — script lists the bundle URL in ASSETS.
    r = client.get(f"/_violetear/pwa/{scope_hash}/sw.js")
    assert r.status_code == 200
    sw = r.text
    assert "CACHE_NAME" in sw
    assert "/_violetear/bundle.py" in sw
    # Pyodide files are pre-cached too so the app loads offline after first visit.
    assert "/_violetear/pyodide/pyodide.js" in sw
    # Cache name includes the pinned app version (1.0.0) so it stays stable
    # across server restarts (the reason we pinned version=).
    assert "1.0.0" in sw

    # Bundle compiles — same canary as 03 but now exercising the PWA bundle
    # too (the long-running `tick()` loop has top-level await semantics).
    r = client.get("/_violetear/bundle.py")
    assert r.status_code == 200
    compile(r.text, "<bundle-04>", "exec", flags=COMPILE_ASYNC)
