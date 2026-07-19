"""Server-side shared state: SharedProxy, SharedRegistry, SharedStateError."""

from __future__ import annotations

import asyncio
import dataclasses
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .app import App


class SharedStateError(Exception):
    """Raised on illegal operations on shared state (e.g. unknown class)."""


class SharedProxy:
    """Wraps a @dataclass instance; intercepts __setattr__ to auto-broadcast."""

    def __init__(self, instance: Any, registry: "SharedRegistry") -> None:
        object.__setattr__(self, "_instance", instance)
        object.__setattr__(self, "_registry", registry)

    def __getattr__(self, name: str) -> Any:
        return getattr(object.__getattribute__(self, "_instance"), name)

    def __setattr__(self, name: str, value: Any) -> None:
        instance = object.__getattribute__(self, "_instance")
        registry = object.__getattribute__(self, "_registry")
        setattr(instance, name, value)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # no running loop (e.g. tests without asyncio)
        loop.create_task(registry.broadcast_sync(type(instance).__name__, name, value))


class SharedRegistry:
    """Owns all @app.shared singletons; drives broadcast and late-joiner push."""

    def __init__(self, app: "App") -> None:
        self._app = app
        self._classes: dict[str, SharedProxy] = {}
        self._meta: dict[str, dict[str, dict]] = {}

    def register(self, cls: type) -> SharedProxy:
        """Instantiate cls, wrap in SharedProxy, register under cls.__name__."""
        if not dataclasses.is_dataclass(cls):
            raise SharedStateError(
                f"{cls.__name__!r} must be a @dataclass to use @app.shared"
            )
        instance = cls()
        proxy = SharedProxy(instance, self)
        self._classes[cls.__name__] = proxy
        self._meta[cls.__name__] = {
            f.name: dict(f.metadata) for f in dataclasses.fields(instance)
        }
        return proxy

    async def broadcast_sync(self, cls_name: str, field: str, value: Any) -> None:
        """Send shared_sync for (cls_name, field, value) to every client."""
        await self._app.socket_manager.broadcast_shared_sync(cls_name, field, value)

    async def push_to_new_client(self, client_id: str) -> None:
        """Push full current state of every @app.shared class to one client."""
        for cls_name, proxy in self._classes.items():
            instance = object.__getattribute__(proxy, "_instance")
            for f in dataclasses.fields(instance):
                value = getattr(instance, f.name)
                await self._app.socket_manager.send_shared_sync(
                    client_id, cls_name, f.name, value
                )

    async def handle_set(
        self, client_id: str, cls_name: str, field: str, value: Any
    ) -> None:
        """Handle inbound shared_set from a client."""
        proxy = self._classes.get(cls_name)
        if proxy is None:
            return  # unknown class — ignore silently
        meta = self._meta.get(cls_name, {}).get(field, {})
        if meta.get("server_only"):
            await self._app.socket_manager.send_shared_error(
                client_id, cls_name, field, "server_only"
            )
            return
        # Apply directly to instance (bypassing SharedProxy to avoid double-broadcast)
        instance = object.__getattribute__(proxy, "_instance")
        try:
            setattr(instance, field, value)
        except Exception:
            await self._app.socket_manager.send_shared_error(
                client_id, cls_name, field, "type_error"
            )
            return
        await self.broadcast_sync(cls_name, field, value)
