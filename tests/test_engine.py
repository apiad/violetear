"""
Engine smoke tests — vertical slice 1.

Covers the request → response → reactive-binding chain at the integration
layer using FastAPI's TestClient. Intentionally light on internal unit tests
of state/dom internals; those follow in slice 2.

Browser-only branches (the IS_BROWSER guards in state.py, dom.py, client.py)
are NOT exercised here — they require a Pyodide simulator and are deferred.
"""
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from violetear import App, Document


# Module-level definitions used by the bundle test.
# The bundle generator (app.py:_generate_bundle) emits user state classes and
# client functions at module scope, so it pulls their source via inspect.getsource.
# If the originals are nested inside another function, the source comes back
# indented and the bundle becomes invalid — see test_bundle_rejects_nested_defs
# below for the pinned bug.
@dataclass
class _BundleState:
    n: int = 0


async def _bundle_click(event):
    pass


def test_view_renders_html_doc():
    """A basic @app.view route returns a fully rendered HTML document."""
    app = App(title="Smoke Test", version="t1")

    @app.view("/")
    def home():
        doc = Document(title="Hello")
        with doc.body as b:
            b.h1("It works")
        return doc

    client = TestClient(app.api)
    r = client.get("/")

    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert r.text.lstrip().startswith("<!DOCTYPE html>")
    assert "<title>Hello</title>" in r.text
    assert "<h1>" in r.text
    assert "It works" in r.text


def test_reactive_ssr_emits_data_bind_for_text_and_value():
    """@app.local proxies passed to .text() / .value() emit data-bind-* companions."""
    app = App(title="Reactive", version="t2")

    @app.local
    @dataclass
    class UiState:
        theme: str = "light"
        username: str = "Guest"

    @app.view("/")
    def home():
        doc = Document(title="Reactive")
        with doc.body as b:
            b.span().text(UiState.theme).id("theme-display")
            b.input(type="text").value(UiState.username).id("name-input")
        return doc

    client = TestClient(app.api)
    html = client.get("/").text

    # Static values rendered for SSR (so first paint is correct before hydration)
    assert "light" in html
    assert 'value="Guest"' in html

    # data-bind-* companions emitted for the client runtime to discover
    assert 'data-bind-text="UiState.theme"' in html
    assert 'data-bind-value="UiState.username"' in html


def test_rpc_endpoint_validates_body_and_returns_result():
    """@app.server.rpc exposes the function via POST /_violetear/rpc/<name> with Pydantic body validation."""
    app = App(title="RPC", version="t3")

    @app.server.rpc
    async def add(x: int, y: int) -> int:
        return x + y

    @app.view("/")
    def home():
        return Document(title="RPC")

    client = TestClient(app.api)

    # Happy path
    r = client.post("/_violetear/rpc/add", json={"x": 2, "y": 3})
    assert r.status_code == 200, r.text
    assert r.json() == 5

    # Pydantic validation: missing field rejected as 422
    r = client.post("/_violetear/rpc/add", json={"x": 2})
    assert r.status_code == 422

    # Pydantic coercion: non-coercible value rejected as 422
    r = client.post("/_violetear/rpc/add", json={"x": "abc", "y": 1})
    assert r.status_code == 422


def test_bundle_endpoint_returns_compilable_python():
    """GET /_violetear/bundle.py returns Pyodide-bound source that is at minimum
    syntactically valid Python — catches regressions in the bundle generator.

    Uses module-level state + callback because the bundle generator expects
    its inputs to be defined at module scope (see test_bundle_rejects_nested_defs)."""
    app = App(title="Bundle", version="t4")
    app.local(_BundleState)
    app.client.callback(_bundle_click)

    @app.view("/")
    def home():
        return Document(title="Bundle")

    client = TestClient(app.api)
    r = client.get("/_violetear/bundle.py")

    assert r.status_code == 200
    assert "text/x-python" in r.headers["content-type"]

    # The bundle must compile under the host Python — surfaces any
    # syntax-breaking regression in _generate_bundle / dedent layout.
    compile(r.text, "<violetear-bundle>", "exec")


@pytest.mark.xfail(
    reason=(
        "Bundle generator (_generate_bundle in app.py:632-634) filters decorator lines "
        "with `c.startswith('@')` instead of `c.strip().startswith('@')`. When a client "
        "function is defined nested inside another function, its source comes back "
        "indented; the decorator line survives the filter and the bundle becomes invalid "
        "Python. Also affects state classes (similar pattern at line 617 uses .strip() "
        "for the decorator but still leaves class body indentation intact). Pinned as a "
        "known limitation: real-world usage defines @app.client.* and @app.local at "
        "module level, where this doesn't bite."
    ),
    strict=True,
)
def test_bundle_rejects_nested_defs():
    """Pin the known limitation: the bundle generator only supports module-level
    state classes and client functions; nested definitions produce invalid bundles."""
    app = App(title="Nested", version="t6")

    @app.local
    @dataclass
    class NestedState:
        n: int = 0

    @app.client.callback
    async def nested_click(event):
        NestedState.n += 1

    @app.view("/")
    def home():
        return Document(title="x")

    client = TestClient(app.api)
    r = client.get("/_violetear/bundle.py")
    compile(r.text, "<violetear-bundle>", "exec")


@pytest.mark.xfail(
    reason=(
        "examples/reactivity.py:73 uses class_name= on b.div(...). Element treats "
        "that as a raw attr (rendered as class_name=\"...\" + data-bind-class_name=...) "
        "instead of class=/data-bind-class. Reactive class bindings aren't supported "
        "by markup.py: self._classes lives outside self._attrs, so the proxy-check at "
        "render time never fires for the class= attribute. Pinned as a known gap "
        "rather than silently fixed."
    ),
    strict=True,
)
def test_reactive_class_binding_emits_data_bind_class():
    """Pin the known gap: there is no first-class way to reactively bind the class= attribute."""
    app = App(title="Class Binding", version="t5")

    @app.local
    @dataclass
    class UiState:
        theme: str = "light"

    @app.view("/")
    def home():
        doc = Document(title="x")
        with doc.body as b:
            b.div(class_name=UiState.theme, id="app-container")
        return doc

    client = TestClient(app.api)
    html = client.get("/").text

    assert 'class="light"' in html
    assert 'data-bind-class="UiState.theme"' in html
