import sys
from typing import cast, Any

# Environment Check: Detect if we are running in the browser (Pyodide)
IS_BROWSER = "pyodide" in sys.modules or "emscripten" in sys.platform


class LeafProxy:
    """
    A wrapper for primitive values (str, int, bool) that allows them to
    be passed around with their 'state path' attached.

    It implements standard dunder methods to behave like the underlying
    primitive in most contexts (comparisons, f-strings, math).
    """
    def __init__(self, value: Any, path: str):
        self._value = value
        self._path = path

    @property
    def current_value(self):
        """Returns the raw primitive value."""
        return self._value

    # --- Type Conversion & Representation ---
    def __str__(self):
        return str(self._value)

    def __repr__(self):
        return repr(self._value)

    def __int__(self):
        return int(self._value)

    def __float__(self):
        return float(self._value)

    def __bool__(self):
        return bool(self._value)

    # --- Equality & hashing ---
    def __eq__(self, other):
        if isinstance(other, LeafProxy):
            return self._value == other._value
        return self._value == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._value)

    # --- Common Math Operations (for counters, etc.) ---
    def __add__(self, other):
        other_val = other._value if isinstance(other, LeafProxy) else other
        return self._value + other_val

    def __radd__(self, other):
        return other + self._value

    def __sub__(self, other):
        other_val = other._value if isinstance(other, LeafProxy) else other
        return self._value - other_val

    def __mul__(self, other):
        other_val = other._value if isinstance(other, LeafProxy) else other
        return self._value * other_val

    # Add other math dunder methods as needed (div, mod, etc.)


class ReactiveProxy:
    """
    A recursive proxy that wraps state objects (classes, dicts, lists).
    It tracks the 'path' to the property being accessed to enable automatic binding.
    """
    def __init__(self, target: Any, path: str = ""):
        # We use object.__setattr__ to avoid triggering our own __setattr__ trap
        object.__setattr__(self, "_target", target)
        object.__setattr__(self, "_path", path)

    @property
    def current_value(self):
        """Returns the raw underlying object."""
        return self._target

    def _is_complex(self, value: Any) -> bool:
        """Determines if a value should be wrapped in a Recursive Proxy."""
        return hasattr(value, "__dict__") or isinstance(value, (dict, list))

    def __getattr__(self, name: str):
        """
        Traps read access to attributes.
        Returns a new Proxy (Reactive or Leaf) wrapping the child attribute.
        """
        # Allow internal python attributes to pass through
        if name.startswith("_"):
            return getattr(self._target, name)

        value = getattr(self._target, name)

        # Build the path: e.g. "UiState" -> "UiState.theme"
        new_path = f"{self._path}.{name}" if self._path else name

        if self._is_complex(value):
            return ReactiveProxy(value, new_path)

        return LeafProxy(value, new_path)

    def __setattr__(self, name: str, value: Any):
        """
        Traps write access.
        1. Updates the underlying source of truth.
        2. If in Browser, notifies the Registry to update the DOM.
        """
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return

        # 1. Update the real object
        setattr(self._target, name, value)

        # 2. Trigger Reactivity (Client-Side Only)
        if IS_BROWSER:
            full_path = f"{self._path}.{name}" if self._path else name
            self._notify_client(full_path, value)

    def __getitem__(self, key: Any):
        """
        Traps dictionary/list read access (e.g. State.users['bob']).
        """
        value = self._target[key]
        new_path = f"{self._path}.{key}" if self._path else str(key)

        if self._is_complex(value):
            return ReactiveProxy(value, new_path)

        return LeafProxy(value, new_path)

    def __setitem__(self, key: Any, value: Any):
        """
        Traps dictionary/list write access.
        """
        self._target[key] = value

        if IS_BROWSER:
            full_path = f"{self._path}.{key}" if self._path else str(key)
            self._notify_client(full_path, value)

    def _notify_client(self, path: str, new_value: Any):
        """
        Lazily imports the client registry to avoid circular imports.
        """
        from violetear.client import ReactiveRegistry
        # We unwrap LeafProxies before sending to the registry if needed,
        # though the registry usually handles the raw value.
        val = new_value._value if isinstance(new_value, LeafProxy) else new_value
        ReactiveRegistry.notify(path, val)


def local[T](cls: type[T]) -> T:
    """
    Decorator: Registers a class as Local State.

    Usage:
        @app.local
        @dataclass
        class Ui:
            theme: str = "light"

    Returns:
        A ReactiveProxy wrapping an instance of the class.
    """
    # Instantiate the user's class
    instance = cls()

    # Use the class name as the root path identifier
    root_path = cls.__name__

    # Create the Root Proxy
    proxy = ReactiveProxy(instance, path=root_path)

    # Return the proxy, but lie to the type checker to preserve IntelliSense for 'cls'
    return cast(T, proxy)
