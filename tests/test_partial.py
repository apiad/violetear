"""Tests for @app.partial — fragment HTML routes."""

import pytest
from fastapi.testclient import TestClient

from violetear.app import App
from violetear.markup import HTML


@pytest.fixture
def app():
    return App(title="Test", version="test")


@pytest.fixture
def client(app):
    return TestClient(app.api)


def test_partial_route_returns_html_fragment(app, client):
    @app.partial("/frag")
    def render_frag():
        ul = HTML.ul()
        ul.add(HTML.li(text="item"))
        return ul

    r = client.get("/frag")
    assert r.status_code == 200
    assert "<ul>" in r.text
    assert "<li>" in r.text


def test_partial_content_type_is_html(app, client):
    @app.partial("/frag2")
    def render_frag2():
        return HTML.div(id="box")

    r = client.get("/frag2")
    assert "text/html" in r.headers["content-type"]


def test_partial_no_document_wrapper(app, client):
    @app.partial("/frag3")
    def render_frag3():
        return HTML.p(text="hello")

    r = client.get("/frag3")
    assert "<html" not in r.text
    assert "<head" not in r.text
    assert "<body" not in r.text
    assert "<p>" in r.text


def test_partial_preserves_attributes(app, client):
    @app.partial("/frag4")
    def render_frag4():
        return HTML.div(id="msg-list", classes="messages")

    r = client.get("/frag4")
    assert 'id="msg-list"' in r.text
    assert "messages" in r.text


def test_partial_multiple_routes(app, client):
    @app.partial("/a")
    def render_a():
        return HTML.span(text="A")

    @app.partial("/b")
    def render_b():
        return HTML.span(text="B")

    assert "A" in client.get("/a").text
    assert "B" in client.get("/b").text


def test_partial_coexists_with_view(app, client):
    @app.partial("/part")
    def render_part():
        return HTML.li(text="partial")

    from violetear.markup import Document

    @app.view("/full")
    def render_full():
        doc = Document(title="Full")
        with doc.body as b:
            b.p(text="full page")
        return doc

    assert "<li>" in client.get("/part").text
    assert "<html" in client.get("/full").text
