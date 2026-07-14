"""Unit tests for violetear/transpile.py — state class and function compilers."""

from dataclasses import dataclass, field

import pytest

from violetear.transpile import ClientCompileError, transpile_class, transpile_function


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


def test_transpile_function_simple_assignment():
    async def fn():
        x = 1
        y = x + 2

    js = transpile_function(fn)
    assert "async function fn()" in js
    assert "let x = 1;" in js
    assert "let y = (x + 2);" in js


def test_transpile_function_if_elif_else():
    async def fn(mode):
        if mode == "a":
            x = 1
        elif mode == "b":
            x = 2
        else:
            x = 3

    js = transpile_function(fn)
    assert 'if (_py.truthy(_py.eq(mode, "a")))' in js
    assert 'else if (_py.truthy(_py.eq(mode, "b")))' in js
    assert "else {" in js


def test_transpile_function_while_loop():
    async def fn(running):
        while running:
            x = 1

    js = transpile_function(fn)
    assert "while (_py.truthy(running))" in js


def test_transpile_function_for_range():
    async def fn():
        for i in range(10):
            x = i

    js = transpile_function(fn)
    assert "for (let i = 0; i < 10; i++)" in js


def test_transpile_function_for_range_start_stop():
    async def fn():
        for i in range(2, 5):
            x = i

    js = transpile_function(fn)
    assert "for (let i = 2; i < 5; i++)" in js


def test_transpile_function_for_items():
    async def fn(users):
        for k, v in users.items():
            x = k

    js = transpile_function(fn)
    assert "for (const [k, v] of Object.entries(users))" in js


def test_transpile_function_for_of():
    async def fn(items):
        for item in items:
            x = item

    js = transpile_function(fn)
    assert "for (const item of items)" in js


def test_transpile_function_await():
    async def fn():
        await save()

    js = transpile_function(fn)
    assert "await save();" in js


def test_transpile_function_augmented_assign():
    async def fn():
        x = 0
        x += 1
        x -= 2

    js = transpile_function(fn)
    assert "x += 1;" in js
    assert "x -= 2;" in js


def test_transpile_function_attribute_assign():
    async def fn():
        UiState.count = 5

    js = transpile_function(fn)
    assert "UiState.count = 5;" in js


def test_transpile_function_try_except():
    async def fn(event):
        try:
            v = float(event.target.value)
        except (ValueError, TypeError):
            return

    js = transpile_function(fn)
    assert "try {" in js
    assert "catch(_e)" in js
    assert "return;" in js


def test_transpile_function_fstring():
    async def fn(name):
        msg = f"hello {name}"

    js = transpile_function(fn)
    assert "let msg = `hello ${name}`;" in js


def test_transpile_function_ternary():
    async def fn(x):
        y = "a" if x else "b"

    js = transpile_function(fn)
    assert '(_py.truthy(x) ? "a" : "b")' in js


def test_transpile_function_is_none():
    async def fn(x):
        if x is None:
            return
        if x is not None:
            y = 1

    js = transpile_function(fn)
    assert "(x === null)" in js
    assert "(x !== null)" in js


def test_transpile_function_floor_div_and_mod():
    async def fn(s):
        m = s // 60
        r = s % 60

    js = transpile_function(fn)
    assert "Math.floor(s / 60)" in js
    assert "(s % 60)" in js


def test_transpile_function_slice():
    async def fn(x):
        a = x[:6]
        b = x[2:]
        c = x[1:4]

    js = transpile_function(fn)
    assert "x.slice(0, 6)" in js
    assert "x.slice(2)" in js
    assert "x.slice(1, 4)" in js


def test_transpile_function_string_methods():
    async def fn(s):
        a = s.strip()
        b = s.upper()
        c = s.startswith("x")

    js = transpile_function(fn)
    assert "s.trim()" in js
    assert "s.toUpperCase()" in js
    assert 's.startsWith("x")' in js


def test_transpile_function_builtin_casts():
    async def fn(x):
        a = int(x)
        b = float(x)
        c = str(x)
        d = bool(x)

    js = transpile_function(fn)
    assert "Math.trunc(Number(x))" in js
    assert "Number(x)" in js
    assert "String(x)" in js
    assert "_py.truthy(x)" in js


def test_transpile_function_math_builtins():
    async def fn(x, y):
        a = abs(x)
        b = round(x)
        c = round(x, 2)
        d = min(x, y)
        e = max(x, y)

    js = transpile_function(fn)
    assert "Math.abs(x)" in js
    assert "Math.round(x)" in js
    assert "parseFloat(x.toFixed(2))" in js
    assert "Math.min(x, y)" in js
    assert "Math.max(x, y)" in js


def test_transpile_function_kwargs_call():
    async def fn(m):
        result = await precise_convert(meters=m)

    js = transpile_function(fn)
    assert "await precise_convert({meters: m})" in js


def test_transpile_function_imports_stripped():
    async def fn():
        import asyncio
        from violetear.js import DOM

        x = 1

    js = transpile_function(fn)
    assert "import" not in js
    assert "asyncio" not in js
    assert "let x = 1;" in js


def test_transpile_function_rejects_sync():
    def fn():
        pass

    with pytest.raises(ClientCompileError, match="async def"):
        transpile_function(fn)


def test_transpile_function_rejects_comprehension():
    async def fn():
        x = [i for i in range(10)]

    with pytest.raises(ClientCompileError, match="unsupported"):
        transpile_function(fn)


def test_transpile_class_setter_validates_field_type():
    @dataclass
    class UiState:
        count: int = 0
        label: str = "x"

    js = transpile_class(UiState)
    assert '(_checkInt)(v, "UiState.count");' in js
    assert '(_checkStr)(v, "UiState.label");' in js
    assert 'ReactiveRegistry.notify("UiState.count", v);' in js


def test_transpile_not_uses_truthy():
    async def fn(items):
        if not items:
            return

    js = transpile_function(fn)
    assert "!_py.truthy(items)" in js


def test_transpile_and_or_short_circuit():
    async def fn(a, b):
        x = a and b
        y = a or b

    js = transpile_function(fn)
    assert "_py.and(a, () => b)" in js
    assert "_py.or(a, () => b)" in js


def test_transpile_eq_ne_use_py():
    async def fn(x, y):
        a = x == y
        b = x != y

    js = transpile_function(fn)
    assert "_py.eq(x, y)" in js
    assert "_py.ne(x, y)" in js


def test_transpile_bool_uses_truthy():
    async def fn(items):
        x = bool(items)

    js = transpile_function(fn)
    assert "_py.truthy(items)" in js


def test_transpile_fstring_format_spec():
    async def fn(n):
        x = f"{n:02d}"

    js = transpile_function(fn)
    assert '`${_py.format(n, "02d")}`' in js


def test_transpile_fstring_plain_unchanged():
    async def fn(name):
        x = f"hello {name}"

    js = transpile_function(fn)
    assert "`hello ${name}`" in js


def test_transpile_fstring_computed_spec_raises():
    async def fn(n, w):
        x = f"{n:{w}d}"

    with pytest.raises(ClientCompileError, match="format spec"):
        transpile_function(fn)
