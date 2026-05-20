"""
Unit-level tests for ClientFunctionStub safety semantics and Element helpers.
"""
import pytest

from violetear import App
from violetear.markup import Element


def test_client_stub_raises_when_called_from_server():
    """The stub returned by @app.client.* must refuse to execute server-side."""
    app = App(version="u1")

    @app.client.callback
    async def on_click(event):
        pass

    with pytest.raises(RuntimeError, match="cannot be called from the Server"):
        on_click(None)


def test_client_callback_stub_repr_distinguishes_kind():
    app = App(version="u2")

    @app.client.callback
    async def cb(event):
        pass

    @app.client
    async def plain():
        pass

    # Repr should distinguish a DOM-binding callback from a plain client function.
    assert "callback" in repr(cb)
    assert "callback" not in repr(plain)
    assert "client:" in repr(plain)


def test_element_on_rejects_non_callback_handler():
    """Element.on requires the handler to carry the @app.client.callback marker."""
    app = App(version="u3")  # noqa: F841 — instantiated to keep the test honest

    async def not_a_callback(event):
        pass

    el = Element("button")
    with pytest.raises(ValueError, match="@app.client.callback"):
        el.on("click", not_a_callback)


def test_element_has_bindings_recurses_through_children():
    """has_bindings finds data-on-* on self or any descendant."""
    app = App(version="u4")

    @app.client.callback
    async def cb(event):
        pass

    parent = Element("div")
    child = Element("button").on("click", cb)
    grandchild = Element("span")

    child.add(grandchild)
    parent.add(child)

    assert parent.has_bindings() is True
    assert child.has_bindings() is True
    assert grandchild.has_bindings() is False


def test_element_has_bindings_ignores_data_bind_attrs():
    """has_bindings counts only data-on-* (event handlers), not data-bind-* (reactive)."""
    el = Element("span")
    el._attrs["data-bind-text"] = "Ui.theme"

    # Pinned: reactive-only elements report no bindings. This is the current
    # contract; if has_bindings is ever made the gate for Pyodide injection,
    # this assertion should flip.
    assert el.has_bindings() is False
