"""Unit tests for violetear/transpile.py — state class and function compilers."""

from dataclasses import dataclass, field

import pytest

from violetear.transpile import ClientCompileError, transpile_class


def test_transpile_class_basic_fields():
    @dataclass
    class Counter:
        count: int = 0
        label: str = "hello"
        active: bool = True

    js = transpile_class(Counter)
    assert "class _Counter {" in js
    assert "const Counter = new _Counter();" in js
    assert "this._count = 0;" in js
    assert 'this._label = "hello";' in js
    assert "this._active = true;" in js
    assert "get count() { return this._count; }" in js
    assert 'ReactiveRegistry.notify("Counter.count", v);' in js


def test_transpile_class_factory_defaults():
    @dataclass
    class State:
        items: list = field(default_factory=list)
        meta: dict = field(default_factory=dict)

    js = transpile_class(State)
    assert "this._items = [];" in js
    assert "this._meta = {};" in js


def test_transpile_class_literal_defaults():
    @dataclass
    class Pomodoro:
        seconds_left: int = 1500
        mode: str = "work"
        running: bool = False

    js = transpile_class(Pomodoro)
    assert "this._seconds_left = 1500;" in js
    assert 'this._mode = "work";' in js
    assert "this._running = false;" in js


def test_transpile_class_singleton_keeps_original_name():
    @dataclass
    class UiState:
        theme: str = "light"

    js = transpile_class(UiState)
    assert "const UiState = new _UiState();" in js
    assert "class _UiState {" in js


def test_transpile_class_rejects_non_dataclass():
    class Plain:
        pass

    with pytest.raises(ClientCompileError, match="@dataclass"):
        transpile_class(Plain)


def test_transpile_class_rejects_user_methods():
    @dataclass
    class Bad:
        count: int = 0

        def increment(self):
            self.count += 1

    with pytest.raises(ClientCompileError, match="must not define methods"):
        transpile_class(Bad)
