import asyncio
import dataclasses
from unittest.mock import AsyncMock, MagicMock
import pytest
from violetear.shared import SharedProxy, SharedRegistry, SharedStateError


@dataclasses.dataclass
class _Counter:
    count: int = 0
    label: str = "x"
    readonly_field: str = dataclasses.field(
        default="locked", metadata={"server_only": True}
    )


def _make_registry(broadcast_fn=None):
    app = MagicMock()
    registry = SharedRegistry(app)
    if broadcast_fn:
        registry.broadcast_sync = broadcast_fn
    return registry


def test_proxy_getattr():
    registry = _make_registry()
    proxy = SharedProxy(_Counter(), registry)
    assert proxy.count == 0
    assert proxy.label == "x"


def test_proxy_setattr_updates_instance():
    calls = []

    async def fake_broadcast(cls, field, value):
        calls.append((cls, field, value))

    registry = _make_registry(fake_broadcast)
    proxy = SharedProxy(_Counter(), registry)

    async def run():
        proxy.__setattr__("count", 42)
        await asyncio.sleep(0)  # let the created task run

    asyncio.run(run())
    assert proxy.count == 42
    assert ("_Counter", "count", 42) in calls


def test_proxy_server_only_write_does_not_raise_from_server():
    # Server writes server_only fields freely — SharedProxy.__setattr__ does NOT raise
    registry = _make_registry(AsyncMock())
    proxy = SharedProxy(_Counter(), registry)
    proxy.readonly_field = "new"  # must not raise
    assert proxy.readonly_field == "new"


# Integration: App.shared decorator
def test_app_shared_decorator_returns_proxy():
    from violetear.app import App
    from violetear.shared import SharedProxy

    app = App(title="test")

    @app.shared
    @dataclasses.dataclass
    class Counter:
        count: int = 0

    assert isinstance(Counter, SharedProxy)
    assert Counter.count == 0


def test_app_shared_registers_in_registry():
    from violetear.app import App

    app = App(title="test")

    @app.shared
    @dataclasses.dataclass
    class Score:
        value: int = 0

    assert "Score" in app.shared_registry._classes


def test_handle_set_updates_and_would_broadcast():
    from violetear.app import App

    app = App(title="test")

    @app.shared
    @dataclasses.dataclass
    class G:
        x: int = 0

    app.socket_manager.broadcast_shared_sync = AsyncMock()

    async def run():
        await app.shared_registry.handle_set("c1", "G", "x", 99)

    asyncio.run(run())
    assert app.shared_registry._classes["G"].x == 99
    app.socket_manager.broadcast_shared_sync.assert_called_once_with("G", "x", 99)


def test_handle_set_rejects_server_only():
    from violetear.app import App

    app = App(title="test")

    @app.shared
    @dataclasses.dataclass
    class H:
        locked: str = dataclasses.field(default="v", metadata={"server_only": True})

    app.socket_manager.send_shared_error = AsyncMock()

    async def run():
        await app.shared_registry.handle_set("c1", "H", "locked", "hacked")

    asyncio.run(run())
    app.socket_manager.send_shared_error.assert_called_once_with(
        "c1", "H", "locked", "server_only"
    )
    assert app.shared_registry._classes["H"].locked == "v"  # unchanged


def test_bundle_contains_shared_class_and_objects_map():
    from violetear.app import App

    app = App(title="test")

    @app.shared
    @dataclasses.dataclass
    class BundleScore:
        value: int = 0

    bundle = app._generate_bundle_js()
    # Shared class emitted with _shared.set in setter
    assert '_shared.set("BundleScore", "value", v)' in bundle
    # _shared_objects map emitted
    assert "_shared_objects = {" in bundle
    assert '"BundleScore": BundleScore' in bundle
