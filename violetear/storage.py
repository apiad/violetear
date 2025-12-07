import sys
import json
from typing import Any, Callable, Union, Iterator, Dict, List

IS_BROWSER = "pyodide" in sys.modules or "emscripten" in sys.platform

if IS_BROWSER:
    from js import localStorage, sessionStorage
    from pyodide.ffi import JsNull


class Thing:
    """
    A smart wrapper for JSON-like data (dicts and lists).
    Allows attribute access (obj.prop) and automatically persists changes.
    """

    def __init__(self, data: Any, on_change: Callable[[], None] = None):
        self._data = data
        # If on_change is None, it's just a passive wrapper (Server side or non-persistent)
        self._on_change = on_change or (lambda: None)

    def __getattr__(self, name: str) -> Any:
        # 1. Allow access to dict keys as attributes
        if isinstance(self._data, dict):
            if name in self._data:
                return self._wrap(self._data[name])
            return None  # JS-like behavior: undefined property is None

        # 2. Forward methods for list (append, etc)
        # This allows store.items.append("new") to trigger a save!
        if hasattr(self._data, name):
            attr = getattr(self._data, name)
            if callable(attr):

                def wrapper(*args, **kwargs):
                    result = attr(*args, **kwargs)
                    self._on_change()  # Trigger save on method call
                    return result

                return wrapper
            return attr

        raise AttributeError(f"'{type(self._data).__name__}' has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any):
        if name.startswith("_"):
            super().__setattr__(name, value)
            return

        if isinstance(self._data, dict):
            # Auto-unwrap if assigning a Thing to a Thing
            if hasattr(value, "unwrap"):
                value = value.unwrap()
            self._data[name] = value
            self._on_change()
        else:
            raise AttributeError("Cannot set attribute on non-dict data")

    def __getitem__(self, key: Union[str, int]) -> Any:
        return self._wrap(self._data[key])

    def __setitem__(self, key: Union[str, int], value: Any):
        if hasattr(value, "unwrap"):
            value = value.unwrap()
        self._data[key] = value
        self._on_change()

    def __delitem__(self, key: Union[str, int]):
        del self._data[key]
        self._on_change()

    def __iter__(self) -> Iterator:
        if isinstance(self._data, (list, tuple)):
            for item in self._data:
                yield self._wrap(item)
        elif isinstance(self._data, dict):
            for key in self._data:
                yield key
        else:
            yield from iter(self._data)

    def __repr__(self):
        return f"{self._data}"

    def __len__(self):
        return len(self._data)

    def _wrap(self, value):
        # Recursively wrap dicts and lists so mutations propagate
        if isinstance(value, (dict, list)):
            return Thing(value, self._on_change)
        return value

    def unwrap(self):
        return self._data


class StorageAPI:
    """
    A Pythonic wrapper around Browser Storage.
    Persists dicts/lists automatically via the Thing wrapper.
    """

    def __init__(self, backend=None):
        self._backend = backend
        # Server-side memory fallback (for testing/mocking)
        self._memory = {}

    def _get_raw(self, key):
        if IS_BROWSER:
            return self._backend.getItem(key)
        return self._memory.get(key)

    def _set_raw(self, key, val):
        if IS_BROWSER:
            self._backend.setItem(key, val)
        else:
            self._memory[key] = val

    def _del_raw(self, key):
        if IS_BROWSER:
            self._backend.removeItem(key)
        else:
            if key in self._memory:
                del self._memory[key]

    def __getattr__(self, key: str) -> Any:
        # Enables 'store.user' syntax
        return self[key]

    def __setattr__(self, key: str, value: Any):
        if key.startswith("_"):
            super().__setattr__(key, value)
            return
        self[key] = value

    def __getitem__(self, key: str) -> Any:
        raw = self._get_raw(key)
        if isinstance(raw, JsNull):
            return None

        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            data = raw

        # Return a Thing that saves back to THIS key when modified.
        # We capture 'data' (the mutable dict/list) in the closure.
        return Thing(data, on_change=lambda: self.__setitem__(key, data))

    def __setitem__(self, key: str, value: Any):
        # Unwrap if it's a Thing
        if hasattr(value, "unwrap"):
            value = value.unwrap()

        self._set_raw(key, json.dumps(value))

    def __delitem__(self, key: str):
        self._del_raw(key)

    def __contains__(self, key: str) -> bool:
        return self._get_raw(key) is not None

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def clear(self):
        if IS_BROWSER:
            self._backend.clear()
        else:
            self._memory.clear()


# --- Instances ---

if IS_BROWSER:
    # Client-Side: Bind to real browser APIs
    store = StorageAPI(localStorage)
    session = StorageAPI(sessionStorage)
else:
    # Server-Side: Bind to stubs (mocks)
    store = StorageAPI()
    session = StorageAPI()
