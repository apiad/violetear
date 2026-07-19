"""Python stubs for browser APIs available in violetear client code.

These classes and functions provide IDE autocompletion and mypy type-checking
for code decorated with @app.client.* — they raise ClientOnlyError if called
server-side. The compiler strips all 'from violetear.js import X' statements
because every export here is a global in runtime.js.

Usage:
    from violetear.js import DOM, Event, localStorage, sleep

Pattern: identical to manifoldx/compute/shader.py — type-correct stubs that
raise on accidental server-side invocation.
"""

from __future__ import annotations

from typing import Any, NoReturn


class ClientOnlyError(RuntimeError):
    """Raised when a browser-only API is called from server-side Python."""


def _client_only(name: str) -> NoReturn:
    raise ClientOnlyError(
        f"{name!r} is a browser-only API. It is only valid inside @app.client.* "
        "functions that are compiled to JavaScript by the violetear compiler. "
        "Do not call it from server-side Python."
    )


# ---------------------------------------------------------------------------
# DOM
# ---------------------------------------------------------------------------


class DOMElement:
    """Wrapper around a live browser DOM element. Browser-only."""

    # --- Content ---
    @property
    def text(self) -> str:
        _client_only("DOMElement.text")

    @text.setter
    def text(self, value: str) -> None:
        _client_only("DOMElement.text")

    @property
    def html(self) -> str:
        _client_only("DOMElement.html")

    @html.setter
    def html(self, content: str) -> None:
        """Set innerHTML without re-hydration. Use load() for reactive content."""
        _client_only("DOMElement.html")

    async def load(self, url: str) -> None:
        """Fetch url, inject as innerHTML, and re-hydrate reactive bindings."""
        _client_only("DOMElement.load")

    # --- Classes ---
    def add_class(self, *names: str) -> "DOMElement":
        _client_only("DOMElement.add_class")

    def remove_class(self, *names: str) -> "DOMElement":
        _client_only("DOMElement.remove_class")

    def toggle_class(self, name: str) -> "DOMElement":
        _client_only("DOMElement.toggle_class")

    def has_class(self, name: str) -> bool:
        _client_only("DOMElement.has_class")

    # --- Attributes ---
    def attr(self, key: str, value: str | None = None) -> "str | DOMElement | None":
        """attr(k, v) sets attribute; attr(k) gets attribute value."""
        _client_only("DOMElement.attr")

    def remove_attr(self, key: str) -> "DOMElement":
        _client_only("DOMElement.remove_attr")

    # --- Visibility ---
    def hide(self) -> "DOMElement":
        _client_only("DOMElement.hide")

    def show(self, display: str = "") -> "DOMElement":
        _client_only("DOMElement.show")

    # --- Form values ---
    @property
    def value(self) -> str:
        _client_only("DOMElement.value")

    @value.setter
    def value(self, v: str) -> None:
        _client_only("DOMElement.value")

    # --- Structure ---
    def clear(self) -> "DOMElement":
        """Set innerHTML to empty string."""
        _client_only("DOMElement.clear")

    def remove(self) -> None:
        """Remove this element from the DOM."""
        _client_only("DOMElement.remove")

    # --- Focus / scroll ---
    def focus(self) -> "DOMElement":
        _client_only("DOMElement.focus")

    def blur(self) -> "DOMElement":
        _client_only("DOMElement.blur")

    def scroll_into_view(self, smooth: bool = True) -> None:
        _client_only("DOMElement.scroll_into_view")

    # --- Events ---
    def on(self, event: str, fn: Any) -> "DOMElement":
        _client_only("DOMElement.on")

    def off(self, event: str, fn: Any) -> "DOMElement":
        _client_only("DOMElement.off")

    # --- Legacy helpers (kept for backward compat with example 05) ---
    def append(self, child: "DOMElement") -> "DOMElement":
        _client_only("DOMElement.append")


class _DatasetProxy:
    def __getattr__(self, name: str) -> str:
        _client_only("dataset")

    def __setattr__(self, name: str, value: Any) -> None:
        _client_only("dataset")


class _EventTarget:
    value: str
    dataset: _DatasetProxy = _DatasetProxy()  # type: ignore[assignment]


class Event:
    """Browser DOM event. Browser-only."""

    target: _EventTarget = _EventTarget()  # type: ignore[assignment]


class _DOM:
    """Provides access to live browser DOM elements. Browser-only."""

    def find(self, id: str) -> DOMElement:
        """getElementById — returns the element with the given id."""
        _client_only("DOM.find")

    def query(self, selector: str) -> DOMElement:
        """querySelector — returns the first matching element."""
        _client_only("DOM.query")

    def query_all(self, selector: str) -> list[DOMElement]:
        """querySelectorAll — returns all matching elements."""
        _client_only("DOM.query_all")

    # Legacy helpers kept for backward compat
    def create(self, tag: str) -> DOMElement:
        _client_only("DOM.create")

    def body(self) -> DOMElement:
        _client_only("DOM.body")


DOM: _DOM = _DOM()  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


class Storage:
    """Sync JSON-transparent key-value store (localStorage or sessionStorage).

    Supports attribute-style access: localStorage.foo = bar
    Keys are namespaced by the app's storage_prefix.
    """

    def get(self, key: str, default: Any = None) -> Any:
        _client_only("Storage.get")

    def set(self, key: str, value: Any) -> None:
        _client_only("Storage.set")

    def remove(self, key: str) -> None:
        _client_only("Storage.remove")

    def has(self, key: str) -> bool:
        _client_only("Storage.has")

    def clear(self) -> None:
        _client_only("Storage.clear")

    def __getattr__(self, key: str) -> Any:
        _client_only("Storage.__getattr__")

    def __setattr__(self, key: str, value: Any) -> None:
        _client_only("Storage.__setattr__")


class IDBStore:
    """Async JSON-transparent key-value store backed by IndexedDB.

    Use for large data or offline-first PWAs. Keys namespaced by storage_prefix.
    No attribute-style access — all methods are async.
    """

    async def get(self, key: str, default: Any = None) -> Any:
        _client_only("IDBStore.get")

    async def set(self, key: str, value: Any) -> None:
        _client_only("IDBStore.set")

    async def remove(self, key: str) -> None:
        _client_only("IDBStore.remove")

    async def has(self, key: str) -> bool:
        _client_only("IDBStore.has")

    async def keys(self) -> list[str]:
        _client_only("IDBStore.keys")

    async def items(self) -> list[tuple[str, Any]]:
        _client_only("IDBStore.items")

    async def clear(self) -> None:
        _client_only("IDBStore.clear")


localStorage: Storage = Storage()
sessionStorage: Storage = Storage()
idb: IDBStore = IDBStore()


# ---------------------------------------------------------------------------
# Network & timing
# ---------------------------------------------------------------------------


class FetchResponse:
    """Response from fetch(). Browser-only."""

    ok: bool = False
    status: int = 0

    async def text(self) -> str:
        _client_only("FetchResponse.text")

    async def json(self) -> Any:
        _client_only("FetchResponse.json")


async def fetch(  # type: ignore[return]
    url: str,
    *,
    method: str = "GET",
    body: str | None = None,
    headers: dict | None = None,
) -> FetchResponse:
    """Browser fetch(). Browser-only."""
    _client_only("fetch")


async def sleep(seconds: float) -> None:  # type: ignore[return]
    """Pause execution for `seconds` seconds. Compiles to setTimeout. Browser-only."""
    _client_only("sleep")


# ---------------------------------------------------------------------------
# Date
# ---------------------------------------------------------------------------


class Date:
    """Wrapper around JS Date. Browser-only."""

    year: int = 0
    month: int = 0
    day: int = 0
    hour: int = 0
    minute: int = 0
    second: int = 0

    @staticmethod
    def now() -> "Date":
        _client_only("Date.now")

    @staticmethod
    def from_iso(s: str) -> "Date":
        _client_only("Date.from_iso")

    def timestamp(self) -> float:
        _client_only("Date.timestamp")

    def to_iso(self) -> str:
        _client_only("Date.to_iso")

    def format(self, fmt: str) -> str:
        _client_only("Date.format")


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def get_client_id() -> str:  # type: ignore[return]
    """Return the per-tab UUID for the current WebSocket connection. Browser-only."""
    _client_only("get_client_id")


class _Console:
    def log(self, *args: Any) -> None:
        _client_only("console.log")

    def error(self, *args: Any) -> None:
        _client_only("console.error")

    def warn(self, *args: Any) -> None:
        _client_only("console.warn")


console: _Console = _Console()


def exec(js_code: str) -> None:  # type: ignore[return]  # noqa: A001
    """Escape hatch: emit raw JS verbatim. Browser-only.

    Example:
        from violetear.js import exec
        exec("window.myLib.init()")
    """
    _client_only("exec")
