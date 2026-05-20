"""
Unit tests for the reactive state proxy (violetear/state.py).

Server-side branches only — IS_BROWSER paths (ReactiveRegistry.notify) are
skipped here; they need a Pyodide simulator and live in a later slice.
"""
from dataclasses import dataclass, field

from violetear.state import LeafProxy, ReactiveProxy, local


def test_local_returns_reactive_proxy_with_root_path():
    @local
    @dataclass
    class Ui:
        theme: str = "light"

    assert isinstance(Ui, ReactiveProxy)
    assert Ui._path == "Ui"
    assert Ui.current_value.theme == "light"


def test_primitive_attribute_returns_leaf_proxy_with_dotted_path():
    @local
    @dataclass
    class Ui:
        theme: str = "light"
        count: int = 5

    theme = Ui.theme
    assert isinstance(theme, LeafProxy)
    assert theme._path == "Ui.theme"
    assert theme.current_value == "light"

    count = Ui.count
    assert isinstance(count, LeafProxy)
    assert count._path == "Ui.count"
    assert count.current_value == 5


def test_nested_object_returns_recursive_proxy():
    @dataclass
    class Inner:
        value: str = "x"

    @local
    @dataclass
    class Outer:
        inner: Inner = field(default_factory=Inner)

    inner_proxy = Outer.inner
    assert isinstance(inner_proxy, ReactiveProxy)
    assert inner_proxy._path == "Outer.inner"

    value_proxy = Outer.inner.value
    assert isinstance(value_proxy, LeafProxy)
    assert value_proxy._path == "Outer.inner.value"
    assert value_proxy.current_value == "x"


def test_dict_access_via_getitem_builds_path():
    @local
    @dataclass
    class Store:
        users: dict = field(default_factory=lambda: {"alice": "admin"})

    role = Store.users["alice"]
    assert isinstance(role, LeafProxy)
    assert role._path == "Store.users.alice"
    assert role.current_value == "admin"


def test_setattr_mutates_underlying_target():
    @local
    @dataclass
    class Ui:
        theme: str = "light"

    Ui.theme = "dark"

    assert Ui.current_value.theme == "dark"
    assert Ui.theme.current_value == "dark"


def test_leaf_proxy_arithmetic_dunders():
    proxy = LeafProxy(5, "x.n")

    assert proxy + 1 == 6
    assert 1 + proxy == 6
    assert proxy - 2 == 3
    assert proxy * 3 == 15
    assert str(proxy) == "5"
    assert int(proxy) == 5
    assert float(proxy) == 5.0
    assert bool(proxy) is True

    zero = LeafProxy(0, "x.n")
    assert bool(zero) is False


def test_leaf_proxy_equality_and_hash():
    a = LeafProxy("light", "x.theme")
    b = LeafProxy("light", "y.theme")  # different path, same value

    assert a == b
    assert a == "light"
    assert a != "dark"
    assert hash(a) == hash("light")


def test_is_complex_classification():
    @dataclass
    class Obj:
        x: int = 1

    proxy = ReactiveProxy(Obj(), "test")

    assert proxy._is_complex({"a": 1}) is True
    assert proxy._is_complex([1, 2, 3]) is True
    assert proxy._is_complex(Obj()) is True
    assert proxy._is_complex("string") is False
    assert proxy._is_complex(42) is False
    assert proxy._is_complex(True) is False
