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


def test_bundle_supports_nested_defs():
    """Bundle generator dedents source so nested @app.local / @app.client defs
    (e.g. inside factories or tests) produce valid Python."""
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
    assert r.status_code == 200
    compile(r.text, "<violetear-bundle>", "exec")


def test_reactive_class_binding_via_classes_kwarg():
    """Passing a state proxy to classes= emits class= (static) + data-bind-class= (binding)."""
    app = App(title="Class Binding", version="t5")

    @app.local
    @dataclass
    class UiState:
        theme: str = "light"

    @app.view("/")
    def home():
        doc = Document(title="x")
        with doc.body as b:
            b.div(classes=UiState.theme, id="app-container")
        return doc

    client = TestClient(app.api)
    html = client.get("/").text

    assert 'class="light"' in html
    assert 'data-bind-class="UiState.theme"' in html


def test_client_on_connect_handler_registered_in_bundle():
    """@app.client.on("connect") handlers are registered in the bundle before hydration,
    so the socket's onopen dispatch finds them. We pin the bundle output rather than
    drive Pyodide; that's a later slice."""
    app = App(title="Connect", version="conn1")

    @app.client.on("connect")
    async def hello():
        pass

    @app.view("/")
    def home():
        return Document(title="x")

    client = TestClient(app.api)
    bundle = client.get("/_violetear/bundle.py").text

    assert "_register_client_event('connect', hello)" in bundle
    # Registration must come before hydrate() so it precedes the socket opening.
    assert bundle.index("_register_client_event('connect', hello)") < bundle.index("hydrate(globals())")
    compile(bundle, "<bundle>", "exec")


def test_client_on_disconnect_handler_registered_in_bundle():
    app = App(title="Disconnect", version="conn2")

    @app.client.on("disconnect")
    async def bye():
        pass

    @app.view("/")
    def home():
        return Document(title="x")

    client = TestClient(app.api)
    bundle = client.get("/_violetear/bundle.py").text

    assert "_register_client_event('disconnect', bye)" in bundle
    compile(bundle, "<bundle>", "exec")


def test_reactive_class_binding_via_class_name_alias():
    """`class_name=` (React-style) is honored as an alias for `classes=`.

    Pythonistas reach for class_name because `class` is a reserved keyword;
    we accept it and route through the same reactive-binding path."""
    app = App(title="Class Name Alias", version="t7")

    @app.local
    @dataclass
    class UiState:
        theme: str = "dark"

    @app.view("/")
    def home():
        doc = Document(title="x")
        with doc.body as b:
            b.div(class_name=UiState.theme, id="x")
        return doc

    client = TestClient(app.api)
    html = client.get("/").text

    assert 'class="dark"' in html
    assert 'data-bind-class="UiState.theme"' in html
    # The alias should be consumed, not leaked as a literal HTML attribute.
    assert "class_name=" not in html
