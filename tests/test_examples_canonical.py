"""
Thin smoke tests for the canonical examples in `examples/0N_*.py`.

Each test verifies that the example module loads, builds, and produces
output with the expected shape. The goal is to catch regressions when
the framework changes — not to validate the examples' behavior in depth.

See `issues/6-canonical-examples-design.md` for the design.
"""

import importlib.util
from pathlib import Path

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def _load(filename: str):
    """Import an example module by filename without it polluting sys.modules."""
    spec = importlib.util.spec_from_file_location(
        filename.removesuffix(".py"), EXAMPLES_DIR / filename
    )
    module = importlib.util.module_from_spec(spec)
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
