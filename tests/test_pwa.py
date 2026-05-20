"""
Tests for PWA route registration, manifest serving, and Service Worker scope.
"""

import hashlib
import json

from fastapi.testclient import TestClient

from violetear import App, Document, Manifest


def _scope_hash(path: str) -> str:
    return hashlib.md5(path.encode()).hexdigest()[:8]


def test_pwa_route_registers_manifest_and_service_worker():
    """@app.view("/foo", pwa=True) exposes manifest + SW under a scope-hashed path."""
    app = App(title="PWA App", version="pwa1")

    @app.view("/install", pwa=True)
    def home():
        return Document(title="PWA")

    h = _scope_hash("/install")
    client = TestClient(app.api)

    r = client.get(f"/_violetear/pwa/{h}/manifest.json")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")

    manifest = json.loads(r.text)
    # Default manifest uses app.title as the name, and backfills scope/start_url
    # from the route path.
    assert manifest["name"] == "PWA App"
    assert manifest["scope"] == "/install"
    assert manifest["start_url"] == "/install"

    r = client.get(f"/_violetear/pwa/{h}/sw.js")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/javascript")
    # Service-Worker-Allowed is required so a SW served from /_violetear/...
    # can control pages at the route's scope.
    assert r.headers["service-worker-allowed"] == "/"


def test_pwa_unknown_scope_returns_404():
    app = App(title="PWA App", version="pwa2")

    @app.view("/")
    def home():
        return Document(title="x")

    client = TestClient(app.api)

    assert client.get("/_violetear/pwa/deadbeef/manifest.json").status_code == 404
    assert client.get("/_violetear/pwa/deadbeef/sw.js").status_code == 404


def test_pwa_custom_manifest_object_is_honored():
    """Passing a Manifest object overrides defaults but inherits scope from the route."""
    app = App(title="App", version="pwa3")

    custom = Manifest(
        name="Custom Name",
        short_name="CN",
        theme_color="#6b21a8",
    )

    @app.view("/app", pwa=custom)
    def home():
        return Document(title="x")

    h = _scope_hash("/app")
    client = TestClient(app.api)
    r = client.get(f"/_violetear/pwa/{h}/manifest.json")
    assert r.status_code == 200

    manifest = json.loads(r.text)
    assert manifest["name"] == "Custom Name"
    assert manifest["short_name"] == "CN"
    assert manifest["theme_color"] == "#6b21a8"
    # The route registration backfills scope/start_url from the route path
    # when the user didn't override them.
    assert manifest["scope"] == "/app"
    assert manifest["start_url"] == "/app"


def test_pwa_service_worker_caches_versioned_bundle_asset():
    """The generated SW script references the versioned bundle URL."""
    app = App(title="App", version="cafef00d")

    @app.view("/", pwa=True)
    def home():
        return Document(title="x")

    h = _scope_hash("/")
    client = TestClient(app.api)
    sw = client.get(f"/_violetear/pwa/{h}/sw.js").text

    # The cache name embeds the app version (sanity check on substitution).
    assert "violetear-cafef00d" in sw
    # The bundle asset is added with the version querystring.
    assert "/_violetear/bundle.py?v=cafef00d" in sw
