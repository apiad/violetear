# violetear v2.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Pyodide with a Python→JS AST compiler (`transpile.py`) and a vanilla-JS runtime (`runtime.js`), so violetear apps load two small scripts instead of 14MB of WASM.

**Architecture:** `@app.local`/`@app.client.*` decorators compile user Python to JS at server startup via `transpile.py`. A new `violetear/runtime.js` (~400 lines) replaces the Pyodide-side Python (ReactiveRegistry, hydration, WebSocket, DOM, storage). A new `violetear/js.py` provides Python stubs for browser APIs for IDE/mypy support — every export is a JS global in `runtime.js`.

**Tech Stack:** Python 3.12+, `ast` stdlib, `inspect.getsource`, vanilla JS (ES2020), FastAPI, pytest, uv.

## Global Constraints

- Python 3.12+ (match statements, `list[str]` generics, `type[T]` syntax).
- `uv run ruff format .` must pass before every commit (`make format-check`).
- Run tests with `uv run pytest tests --cov=violetear`.
- All client handler functions must be `async def` — enforced by compiler.
- No third-party JS dependencies in `runtime.js` — vanilla JS only.
- `ClientCompileError` raised at decoration time (server startup), not at runtime.
- All kwargs-only Python function calls compile to JS object-destructured calls: `fn(k=v)` → `fn({k: v})`.
- State class JS singleton keeps the original class name: `const UiState = new _UiState()`.
- `from violetear.js import X` inside client functions is stripped by the compiler — X is a JS global.
- No deprecated shims: `client.py`, `dom.py`, `storage.py` are fully deleted.
- Test gate: `make test-unit` (= `make format-check` + `uv run pytest tests --cov=violetear`).

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `violetear/transpile.py` | **Create** | Python→JS AST compiler: `ClientCompileError`, `transpile_class`, `transpile_function` |
| `violetear/js.py` | **Create** | Python stubs for browser APIs — raises `ClientOnlyError` server-side |
| `violetear/runtime.js` | **Create** | Vanilla JS runtime: ReactiveRegistry, hydration, WebSocket, DOM, Storage, IDB |
| `violetear/app.py` | **Modify** | Remove Pyodide machinery; wire compiler at decoration time; new bundle.js + runtime.js routes |
| `violetear/client.py` | **Delete** | Replaced by runtime.js |
| `violetear/dom.py` | **Delete** | Replaced by violetear/js.py + runtime.js |
| `violetear/storage.py` | **Delete** | Replaced by violetear/js.py + runtime.js |
| `tests/test_transpile.py` | **Create** | Unit tests for both compilers |
| `tests/test_js_shims.py` | **Create** | Unit tests for js.py stubs |
| `tests/test_unit.py` | **Modify** | Remove Pyodide-era tests; add compiler-error tests |
| `tests/test_examples_canonical.py` | **Modify** | Update for bundle.js endpoint (was bundle.py) |
| `examples/03_interactive.py` | **Modify** | Update to `from violetear.js import ...` |
| `examples/04_pwa.py` | **Modify** | Same + `asyncio.sleep` → `sleep` |
| `examples/05_realtime.py` | **Modify** | Same |
| `pyproject.toml` | **Modify** | Version 1.2.4 → 2.0.0 |
| `violetear/__init__.py` | **Modify** | Version string 1.2.4 → 2.0.0 |

---

### Task 1: `ClientCompileError` + state class compiler

**Files:**
- Create: `violetear/transpile.py`
- Create: `tests/test_transpile.py`

**Interfaces:**
- Produces: `ClientCompileError`, `transpile_class(cls: type) -> str`

- [ ] **Step 1: Create `violetear/transpile.py` with `ClientCompileError` and `transpile_class`**

```python
"""Python→JS AST compiler for violetear client-side code."""
from __future__ import annotations

import dataclasses
import json
from typing import Any


class ClientCompileError(Exception):
    """Raised when client-side Python cannot be compiled to JS.

    Structured like a compiler error: file, line, col, category, message.
    """

    def __init__(
        self,
        *,
        category: str,
        message: str,
        filename: str,
        line: int,
        col: int,
        source_line: str | None = None,
    ):
        self.category = category
        self.message = message
        self.filename = filename
        self.line = line
        self.col = col
        self.source_line = source_line
        super().__init__(self._render())

    def _render(self) -> str:
        head = f"{self.filename}:{self.line}:{self.col}: {self.category}: {self.message}"
        if self.source_line:
            caret = " " * self.col + "^"
            return f"{head}\n  {self.source_line}\n  {caret}"
        return head


_TYPE_DEFAULTS: dict[type, str] = {
    int: "0",
    float: "0.0",
    str: '""',
    bool: "false",
    list: "[]",
    dict: "{}",
}


def _py_value_to_js(val: Any) -> str:
    """Convert a Python literal value to a JS literal string."""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        return repr(val)
    if isinstance(val, str):
        return json.dumps(val)
    if isinstance(val, list) and not val:
        return "[]"
    if isinstance(val, dict) and not val:
        return "{}"
    raise ClientCompileError(
        category="unsupported-construct",
        message=f"unsupported default value type: {type(val).__name__!r} ({val!r}); "
                "use int, float, str, bool, or empty list/dict",
        filename="<default>",
        line=0,
        col=0,
    )


def _js_field_default(field: dataclasses.Field) -> str:
    """Return the JS default literal for a dataclass field."""
    if field.default is not dataclasses.MISSING:
        return _py_value_to_js(field.default)
    if field.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
        val = field.default_factory()  # type: ignore[misc]
        return _py_value_to_js(val)
    # Fall back to type annotation
    tp = field.type if isinstance(field.type, type) else None
    if tp in _TYPE_DEFAULTS:
        return _TYPE_DEFAULTS[tp]
    return "null"


def transpile_class(cls: type) -> str:
    """Compile an @app.local @dataclass to a reactive JS class + singleton.

    The singleton keeps the original class name so Python code translates 1:1:
        const UiState = new _UiState();
    User code writes UiState.meters in both Python and JS without name changes.

    Raises ClientCompileError for non-dataclasses or classes with user methods.
    """
    if not dataclasses.is_dataclass(cls):
        raise ClientCompileError(
            category="unsupported-construct",
            message=f"{cls.__name__!r} must be decorated with @dataclass",
            filename=getattr(cls, "__module__", "<class>"),
            line=0,
            col=0,
        )

    class_name = cls.__name__
    user_methods = [
        name
        for name, val in cls.__dict__.items()
        if callable(val) and not name.startswith("_")
    ]
    if user_methods:
        raise ClientCompileError(
            category="unsupported-construct",
            message=f"state class {class_name!r} must not define methods; "
                    f"found: {user_methods!r}. Use @app.client functions instead.",
            filename=getattr(cls, "__module__", "<class>"),
            line=0,
            col=0,
        )

    fields = dataclasses.fields(cls)
    lines: list[str] = [f"class _{class_name} {{", "  constructor() {"]
    for f in fields:
        lines.append(f"    this._{f.name} = {_js_field_default(f)};")
    lines.append("  }")

    for f in fields:
        lines.append(f"  get {f.name}() {{ return this._{f.name}; }}")
        lines.append(
            f"  set {f.name}(v) {{ "
            f'this._{f.name} = v; '
            f'ReactiveRegistry.notify("{class_name}.{f.name}", v); }}'
        )

    lines.append("}")
    lines.append(f"const {class_name} = new _{class_name}();")
    return "\n".join(lines)
```

- [ ] **Step 2: Write failing tests for `transpile_class`**

```python
# tests/test_transpile.py
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
```

- [ ] **Step 3: Run tests — expect FAIL (module doesn't exist yet)**

```bash
cd repos/violetear && uv run pytest tests/test_transpile.py -v
```
Expected: `ModuleNotFoundError` or all FAIL.

- [ ] **Step 4: Run tests — expect PASS**

```bash
uv run pytest tests/test_transpile.py -v
```
Expected: all 6 tests PASS.

- [ ] **Step 5: Format and commit**

```bash
uv run ruff format violetear/transpile.py tests/test_transpile.py
git add violetear/transpile.py tests/test_transpile.py
git commit -m "feat(transpile): ClientCompileError + transpile_class for @app.local dataclasses"
```

---

### Task 2: Function compiler — core statement + expression subset

**Files:**
- Modify: `violetear/transpile.py`
- Modify: `tests/test_transpile.py`

**Interfaces:**
- Consumes: `ClientCompileError` from Task 1
- Produces: `transpile_function(fn) -> str`

- [ ] **Step 1: Add `_CompileContext`, `_emit_block`, `_emit_stmt`, `_emit_expr`, and `transpile_function` to `violetear/transpile.py`**

Append to `violetear/transpile.py`:

```python
import ast
import inspect
import textwrap


_BIN_OPS: dict[type, str] = {
    ast.Add: "+", ast.Sub: "-", ast.Mult: "*",
    ast.Div: "/", ast.Mod: "%",
}

_AUG_OPS: dict[type, str] = {
    ast.Add: "+", ast.Sub: "-", ast.Mult: "*",
    ast.Div: "/", ast.Mod: "%",
}

_CMP_OPS: dict[type, str] = {
    ast.Eq: "===", ast.NotEq: "!==",
    ast.Lt: "<", ast.LtE: "<=",
    ast.Gt: ">", ast.GtE: ">=",
}

_STRING_METHODS: dict[str, str] = {
    "strip": "trim",
    "upper": "toUpperCase",
    "lower": "toLowerCase",
    "startswith": "startsWith",
    "endswith": "endsWith",
    "split": "split",
}


class _CompileContext:
    """Tracks declared variable names within a single function body."""

    def __init__(self, filename: str):
        self.filename = filename
        self._declared: set[str] = set()

    def declare(self, name: str) -> str:
        """Return 'let <name>' on first use, '<name>' on reassignment."""
        if name not in self._declared:
            self._declared.add(name)
            return f"let {name}"
        return name


def _emit_block(stmts: list[ast.stmt], ctx: _CompileContext) -> str:
    lines: list[str] = []
    for s in stmts:
        text = _emit_stmt(s, ctx)
        if not text:
            continue
        for ln in text.splitlines():
            lines.append(f"  {ln}")
    return "\n".join(lines)


def _emit_stmt(node: ast.stmt, ctx: _CompileContext) -> str:  # noqa: C901
    # Strip all imports — violetear.js symbols are globals in runtime.js
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return ""

    if isinstance(node, ast.Pass):
        return ""

    if isinstance(node, ast.AnnAssign):
        if node.value is None:
            return ""  # annotation-only declaration
        if not isinstance(node.target, ast.Name):
            raise ClientCompileError(
                category="unsupported-construct",
                message="annotated assignment target must be a plain name",
                filename=ctx.filename, line=node.lineno, col=node.col_offset,
            )
        rhs = _emit_expr(node.value, ctx)
        lhs = ctx.declare(node.target.id)
        return f"{lhs} = {rhs};"

    if isinstance(node, ast.Assign):
        if len(node.targets) != 1:
            raise ClientCompileError(
                category="unsupported-construct",
                message="multi-target assignment (a = b = c) is not supported",
                filename=ctx.filename, line=node.lineno, col=node.col_offset,
            )
        target = node.targets[0]
        rhs = _emit_expr(node.value, ctx)
        return _emit_assignment_target(target, rhs, None, ctx, node.lineno, node.col_offset)

    if isinstance(node, ast.AugAssign):
        op = _AUG_OPS.get(type(node.op))
        if op is None:
            raise ClientCompileError(
                category="unsupported-construct",
                message=f"unsupported augmented operator {type(node.op).__name__}; "
                        "use +, -, *, /, %",
                filename=ctx.filename, line=node.lineno, col=node.col_offset,
            )
        rhs = _emit_expr(node.value, ctx)
        return _emit_assignment_target(node.target, rhs, op, ctx, node.lineno, node.col_offset)

    if isinstance(node, ast.If):
        cond = _emit_expr(node.test, ctx)
        body = _emit_block(node.body, ctx)
        out = f"if ({cond}) {{\n{body}\n}}"
        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                elif_text = _emit_stmt(node.orelse[0], ctx)
                out += f" else {elif_text}"
            else:
                else_body = _emit_block(node.orelse, ctx)
                out += f" else {{\n{else_body}\n}}"
        return out

    if isinstance(node, ast.While):
        cond = _emit_expr(node.test, ctx)
        body = _emit_block(node.body, ctx)
        return f"while ({cond}) {{\n{body}\n}}"

    if isinstance(node, ast.For):
        return _emit_for(node, ctx)

    if isinstance(node, ast.Return):
        if node.value is None:
            return "return;"
        return f"return {_emit_expr(node.value, ctx)};"

    if isinstance(node, ast.Try):
        if len(node.handlers) != 1:
            raise ClientCompileError(
                category="unsupported-construct",
                message="only a single except clause is supported; split into multiple try blocks",
                filename=ctx.filename, line=node.lineno, col=node.col_offset,
            )
        body = _emit_block(node.body, ctx)
        catch_body = _emit_block(node.handlers[0].body, ctx)
        return f"try {{\n{body}\n}} catch(_e) {{\n{catch_body}\n}}"

    if isinstance(node, ast.Expr):
        val = node.value
        if isinstance(val, ast.Await):
            return f"await {_emit_expr(val.value, ctx)};"
        return f"{_emit_expr(val, ctx)};"

    if isinstance(node, ast.Break):
        return "break;"

    if isinstance(node, ast.Continue):
        return "continue;"

    raise ClientCompileError(
        category="unsupported-construct",
        message=f"unsupported statement: {ast.unparse(node)!r}",
        filename=ctx.filename,
        line=getattr(node, "lineno", 0),
        col=getattr(node, "col_offset", 0),
    )


def _emit_assignment_target(
    target: ast.expr, rhs: str, aug_op: str | None,
    ctx: _CompileContext, line: int, col: int,
) -> str:
    if isinstance(target, ast.Name):
        if aug_op is not None:
            return f"{target.id} {aug_op}= {rhs};"
        lhs = ctx.declare(target.id)
        return f"{lhs} = {rhs};"
    if isinstance(target, ast.Attribute):
        obj = _emit_expr(target.value, ctx)
        if aug_op is not None:
            return f"{obj}.{target.attr} {aug_op}= {rhs};"
        return f"{obj}.{target.attr} = {rhs};"
    if isinstance(target, ast.Subscript):
        obj = _emit_expr(target.value, ctx)
        key = _emit_expr(target.slice, ctx)
        if aug_op is not None:
            return f"{obj}[{key}] {aug_op}= {rhs};"
        return f"{obj}[{key}] = {rhs};"
    raise ClientCompileError(
        category="unsupported-construct",
        message=f"unsupported assignment target: {ast.unparse(target)!r}",
        filename=ctx.filename, line=line, col=col,
    )


def _emit_for(node: ast.For, ctx: _CompileContext) -> str:
    # range() loop
    if (
        isinstance(node.iter, ast.Call)
        and isinstance(node.iter.func, ast.Name)
        and node.iter.func.id == "range"
    ):
        if not isinstance(node.target, ast.Name):
            raise ClientCompileError(
                category="unsupported-construct",
                message="for-range loop target must be a plain name",
                filename=ctx.filename, line=node.lineno, col=node.col_offset,
            )
        args = node.iter.args
        if len(args) == 1:
            start, stop = "0", _emit_expr(args[0], ctx)
        elif len(args) == 2:
            start = _emit_expr(args[0], ctx)
            stop = _emit_expr(args[1], ctx)
        else:
            raise ClientCompileError(
                category="unsupported-construct",
                message="range(start, stop, step) — step not supported",
                filename=ctx.filename, line=node.lineno, col=node.col_offset,
            )
        v = node.target.id
        ctx._declared.add(v)
        body = _emit_block(node.body, ctx)
        return f"for (let {v} = {start}; {v} < {stop}; {v}++) {{\n{body}\n}}"

    # dict.items() loop — for k, v in d.items()
    if (
        isinstance(node.iter, ast.Call)
        and isinstance(node.iter.func, ast.Attribute)
        and node.iter.func.attr == "items"
    ):
        if not (isinstance(node.target, ast.Tuple) and len(node.target.elts) == 2):
            raise ClientCompileError(
                category="unsupported-construct",
                message="for ... in d.items() requires exactly two loop variables: for k, v in d.items()",
                filename=ctx.filename, line=node.lineno, col=node.col_offset,
            )
        k = node.target.elts[0]
        v = node.target.elts[1]
        if not (isinstance(k, ast.Name) and isinstance(v, ast.Name)):
            raise ClientCompileError(
                category="unsupported-construct",
                message="for-items loop variables must be plain names",
                filename=ctx.filename, line=node.lineno, col=node.col_offset,
            )
        ctx._declared.add(k.id)
        ctx._declared.add(v.id)
        obj = _emit_expr(node.iter.func.value, ctx)
        body = _emit_block(node.body, ctx)
        return f"for (const [{k.id}, {v.id}] of Object.entries({obj})) {{\n{body}\n}}"

    # generic for-of loop
    if not isinstance(node.target, ast.Name):
        raise ClientCompileError(
            category="unsupported-construct",
            message="for-loop target must be a plain name (tuple unpacking only supported with .items())",
            filename=ctx.filename, line=node.lineno, col=node.col_offset,
        )
    v = node.target.id
    ctx._declared.add(v)
    iterable = _emit_expr(node.iter, ctx)
    body = _emit_block(node.body, ctx)
    return f"for (const {v} of {iterable}) {{\n{body}\n}}"


def _emit_expr(node: ast.expr, ctx: _CompileContext) -> str:  # noqa: C901
    if isinstance(node, ast.Constant):
        v = node.value
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return repr(v)
        if isinstance(v, str):
            return json.dumps(v)
        raise ClientCompileError(
            category="unsupported-construct",
            message=f"unsupported literal type: {type(v).__name__!r}",
            filename=ctx.filename, line=node.lineno, col=node.col_offset,
        )

    if isinstance(node, ast.Name):
        return node.id  # None/True/False are ast.Constant in Python 3.8+

    if isinstance(node, ast.Attribute):
        obj = _emit_expr(node.value, ctx)
        return f"{obj}.{node.attr}"

    if isinstance(node, ast.Subscript):
        obj = _emit_expr(node.value, ctx)
        slc = node.slice
        if isinstance(slc, ast.Slice):
            lower = _emit_expr(slc.lower, ctx) if slc.lower else "0"
            if slc.upper is None:
                return f"{obj}.slice({lower})"
            upper = _emit_expr(slc.upper, ctx)
            return f"{obj}.slice({lower}, {upper})"
        key = _emit_expr(slc, ctx)
        return f"{obj}[{key}]"

    if isinstance(node, ast.Call):
        return _emit_call(node, ctx)

    if isinstance(node, ast.BinOp):
        l = _emit_expr(node.left, ctx)
        r = _emit_expr(node.right, ctx)
        if isinstance(node.op, ast.FloorDiv):
            return f"Math.floor({l} / {r})"
        if isinstance(node.op, ast.Pow):
            return f"Math.pow({l}, {r})"
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise ClientCompileError(
                category="unsupported-construct",
                message=f"unsupported binary operator {type(node.op).__name__}",
                filename=ctx.filename, line=node.lineno, col=node.col_offset,
            )
        return f"({l} {op} {r})"

    if isinstance(node, ast.UnaryOp):
        v = _emit_expr(node.operand, ctx)
        if isinstance(node.op, ast.USub):
            return f"(-{v})"
        if isinstance(node.op, ast.Not):
            return f"(!{v})"
        if isinstance(node.op, ast.UAdd):
            return v
        raise ClientCompileError(
            category="unsupported-construct",
            message=f"unsupported unary operator {type(node.op).__name__}",
            filename=ctx.filename, line=node.lineno, col=node.col_offset,
        )

    if isinstance(node, ast.BoolOp):
        op = "&&" if isinstance(node.op, ast.And) else "||"
        parts = [_emit_expr(v, ctx) for v in node.values]
        return "(" + f" {op} ".join(parts) + ")"

    if isinstance(node, ast.Compare):
        if len(node.ops) != 1:
            raise ClientCompileError(
                category="unsupported-construct",
                message="chained comparisons not supported; use explicit and/or",
                filename=ctx.filename, line=node.lineno, col=node.col_offset,
            )
        l = _emit_expr(node.left, ctx)
        comparator = node.comparators[0]
        op = node.ops[0]
        # is None / is not None
        if isinstance(op, ast.Is) and isinstance(comparator, ast.Constant) and comparator.value is None:
            return f"({l} === null)"
        if isinstance(op, ast.IsNot) and isinstance(comparator, ast.Constant) and comparator.value is None:
            return f"({l} !== null)"
        cmp_op = _CMP_OPS.get(type(op))
        if cmp_op is None:
            raise ClientCompileError(
                category="unsupported-construct",
                message=f"unsupported comparison {type(op).__name__}; "
                        "use ==, !=, <, <=, >, >= or 'is None' / 'is not None'",
                filename=ctx.filename, line=node.lineno, col=node.col_offset,
            )
        r = _emit_expr(comparator, ctx)
        return f"({l} {cmp_op} {r})"

    if isinstance(node, ast.IfExp):
        cond = _emit_expr(node.test, ctx)
        body = _emit_expr(node.body, ctx)
        orelse = _emit_expr(node.orelse, ctx)
        return f"({cond} ? {body} : {orelse})"

    if isinstance(node, ast.JoinedStr):  # f-string
        parts: list[str] = []
        for val in node.values:
            if isinstance(val, ast.Constant):
                parts.append(val.value.replace("`", "\\`").replace("${", "\\${"))
            elif isinstance(val, ast.FormattedValue):
                expr = _emit_expr(val.value, ctx)
                parts.append(f"${{{expr}}}")
            else:
                raise ClientCompileError(
                    category="unsupported-construct",
                    message="unsupported f-string component",
                    filename=ctx.filename, line=node.lineno, col=node.col_offset,
                )
        return "`" + "".join(parts) + "`"

    if isinstance(node, ast.List):
        elts = [_emit_expr(e, ctx) for e in node.elts]
        return f"[{', '.join(elts)}]"

    if isinstance(node, ast.Dict):
        pairs = []
        for k, v in zip(node.keys, node.values):
            pairs.append(f"{_emit_expr(k, ctx)}: {_emit_expr(v, ctx)}")
        return "{" + ", ".join(pairs) + "}"

    if isinstance(node, ast.Tuple):
        elts = [_emit_expr(e, ctx) for e in node.elts]
        return f"[{', '.join(elts)}]"

    if isinstance(node, ast.Await):
        return f"await {_emit_expr(node.value, ctx)}"

    raise ClientCompileError(
        category="unsupported-construct",
        message=f"unsupported expression: {ast.unparse(node)!r}",
        filename=ctx.filename,
        line=getattr(node, "lineno", 0),
        col=getattr(node, "col_offset", 0),
    )


def _emit_call(node: ast.Call, ctx: _CompileContext) -> str:
    """Emit a JS call expression, handling builtin translations and kwargs."""
    pos_args = [_emit_expr(a, ctx) for a in node.args]
    kw_args = {kw.arg: _emit_expr(kw.value, ctx) for kw in node.keywords if kw.arg}

    if pos_args and kw_args:
        raise ClientCompileError(
            category="unsupported-construct",
            message="mixing positional and keyword arguments is not supported; use one or the other",
            filename=ctx.filename, line=node.lineno, col=node.col_offset,
        )

    func = node.func

    # Named function call
    if isinstance(func, ast.Name):
        fname = func.id
        translated = _try_builtin(fname, pos_args, kw_args, ctx, node)
        if translated is not None:
            return translated
        if kw_args:
            kw_str = ", ".join(f"{k}: {v}" for k, v in kw_args.items())
            return f"{fname}({{{kw_str}}})"
        return f"{fname}({', '.join(pos_args)})"

    # Method call
    if isinstance(func, ast.Attribute):
        obj = _emit_expr(func.value, ctx)
        method = func.attr

        # String method translations
        if method in _STRING_METHODS:
            js_method = _STRING_METHODS[method]
            return f"{obj}.{js_method}({', '.join(pos_args)})"

        # str.join(lst) — reversed receiver in JS: lst.join(sep)
        if method == "join" and pos_args:
            return f"{pos_args[0]}.join({obj})"

        if kw_args:
            kw_str = ", ".join(f"{k}: {v}" for k, v in kw_args.items())
            return f"{obj}.{method}({{{kw_str}}})"
        return f"{obj}.{method}({', '.join(pos_args)})"

    raise ClientCompileError(
        category="unsupported-construct",
        message=f"unsupported call form: {ast.unparse(node)!r}",
        filename=ctx.filename, line=node.lineno, col=node.col_offset,
    )


def _try_builtin(
    fname: str, pos_args: list[str], kw_args: dict[str, str],
    ctx: _CompileContext, node: ast.Call,
) -> str | None:
    """Return a JS translation for a recognized Python builtin, or None."""
    match fname:
        case "int":
            return f"Math.trunc(Number({pos_args[0]}))" if pos_args else "0"
        case "float":
            return f"Number({pos_args[0]})" if pos_args else "0.0"
        case "str":
            return f"String({pos_args[0]})" if pos_args else '""'
        case "bool":
            return f"Boolean({pos_args[0]})" if pos_args else "false"
        case "len":
            return f"{pos_args[0]}.length"
        case "print":
            return f"console.log({', '.join(pos_args)})"
        case "abs":
            return f"Math.abs({pos_args[0]})"
        case "round":
            if len(pos_args) == 1:
                return f"Math.round({pos_args[0]})"
            return f"parseFloat({pos_args[0]}.toFixed({pos_args[1]}))"
        case "min":
            if len(pos_args) != 2:
                raise ClientCompileError(
                    category="unsupported-construct",
                    message="min() requires exactly 2 scalar arguments; list form not supported",
                    filename=ctx.filename, line=node.lineno, col=node.col_offset,
                )
            return f"Math.min({pos_args[0]}, {pos_args[1]})"
        case "max":
            if len(pos_args) != 2:
                raise ClientCompileError(
                    category="unsupported-construct",
                    message="max() requires exactly 2 scalar arguments; list form not supported",
                    filename=ctx.filename, line=node.lineno, col=node.col_offset,
                )
            return f"Math.max({pos_args[0]}, {pos_args[1]})"
        case "pow":
            return f"Math.pow({pos_args[0]}, {pos_args[1]})"
        case "sum":
            raise ClientCompileError(
                category="unsupported-construct",
                message="sum() is not supported; use a for loop",
                filename=ctx.filename, line=node.lineno, col=node.col_offset,
            )
        case "isinstance":
            raise ClientCompileError(
                category="unsupported-construct",
                message="isinstance() is not supported in client code",
                filename=ctx.filename, line=node.lineno, col=node.col_offset,
            )
        case "exec":
            # violetear.js escape hatch — emit the JS string literally
            if pos_args:
                raw = pos_args[0]
                # Strip surrounding quotes if it's a string literal
                return raw.strip('"').strip("'").strip("`")
            return ""
    return None


def transpile_function(fn) -> str:
    """Compile a @app.client.* async def to a JS async function.

    All imports inside the function body are stripped — violetear.js symbols
    are globals in runtime.js. Raises ClientCompileError at decoration time
    for any unsupported construct.
    """
    src = textwrap.dedent(inspect.getsource(fn))
    tree = ast.parse(src)
    func_def = tree.body[0]

    if not isinstance(func_def, ast.AsyncFunctionDef):
        raise ClientCompileError(
            category="unsupported-construct",
            message=f"{fn.__name__!r} must be async def; client handlers are always async",
            filename=fn.__code__.co_filename,
            line=getattr(func_def, "lineno", 0),
            col=getattr(func_def, "col_offset", 0),
        )

    params = [a.arg for a in func_def.args.args]
    ctx = _CompileContext(filename=fn.__code__.co_filename)
    # Pre-declare params so they don't get 'let' prefix inside the body
    ctx._declared.update(params)

    body_lines: list[str] = []
    for stmt in func_def.body:
        text = _emit_stmt(stmt, ctx)
        if text:
            body_lines.append(text)

    body = "\n".join(f"  {ln}" for chunk in body_lines for ln in chunk.splitlines())
    param_str = ", ".join(params)
    return f"async function {fn.__name__}({param_str}) {{\n{body}\n}}"
```

- [ ] **Step 2: Add function compiler tests**

Append to `tests/test_transpile.py`:

```python
from violetear.transpile import transpile_function


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
    assert 'if ((mode === "a"))' in js
    assert 'else if ((mode === "b"))' in js
    assert "else {" in js


def test_transpile_function_while_loop():
    async def fn(running):
        while running:
            x = 1

    js = transpile_function(fn)
    assert "while (running)" in js


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
    assert '(x ? "a" : "b")' in js


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
    assert "Boolean(x)" in js


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
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tests/test_transpile.py -v
```
Expected: all tests PASS.

- [ ] **Step 4: Format and commit**

```bash
uv run ruff format violetear/transpile.py tests/test_transpile.py
git add violetear/transpile.py tests/test_transpile.py
git commit -m "feat(transpile): transpile_function — full Python→JS AST compiler subset"
```

---

### Task 3: `violetear/js.py` — browser API shims

**Files:**
- Create: `violetear/js.py`
- Create: `tests/test_js_shims.py`

**Interfaces:**
- Produces: `ClientOnlyError`, `DOM`, `DOMElement`, `Event`, `Storage`, `IDBStore`, `FetchResponse`, `Date`, `localStorage`, `sessionStorage`, `idb`, `console`, `sleep`, `fetch`, `get_client_id`, `exec`

- [ ] **Step 1: Create `violetear/js.py`**

```python
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
    """Wrapper around a browser DOM element. Browser-only."""

    @property
    def text(self) -> str:
        _client_only("DOMElement.text")

    @text.setter
    def text(self, value: Any) -> None:
        _client_only("DOMElement.text")

    @property
    def html(self) -> str:
        _client_only("DOMElement.html")

    @html.setter
    def html(self, value: Any) -> None:
        _client_only("DOMElement.html")

    @property
    def value(self) -> Any:
        _client_only("DOMElement.value")

    @value.setter
    def value(self, v: Any) -> None:
        _client_only("DOMElement.value")

    def add(self, *classes: str) -> "DOMElement":
        _client_only("DOMElement.add")

    def remove(self, *classes: str) -> "DOMElement":
        _client_only("DOMElement.remove")

    def toggle(self, cls: str, force: bool | None = None) -> "DOMElement":
        _client_only("DOMElement.toggle")

    def append(self, child: "DOMElement") -> "DOMElement":
        _client_only("DOMElement.append")

    def attr(self, name: str, value: Any = None) -> "DOMElement | str | None":
        _client_only("DOMElement.attr")

    def on(self, event: str, handler: Any) -> "DOMElement":
        _client_only("DOMElement.on")

    def query(self, selector: str) -> list["DOMElement"]:
        _client_only("DOMElement.query")


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


class DOM:
    """Static factory for DOM elements. Browser-only."""

    @staticmethod
    def find(id: str) -> DOMElement:
        _client_only("DOM.find")

    @staticmethod
    def create(tag: str) -> DOMElement:
        _client_only("DOM.create")

    @staticmethod
    def query(selector: str) -> list[DOMElement]:
        _client_only("DOM.query")

    @staticmethod
    def body() -> DOMElement:
        _client_only("DOM.body")


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
```

- [ ] **Step 2: Write tests for js.py**

```python
# tests/test_js_shims.py
"""Tests that violetear.js stubs raise ClientOnlyError when called server-side."""
import pytest
from violetear.js import (
    ClientOnlyError, DOM, DOMElement, Event, Storage, IDBStore,
    localStorage, sessionStorage, idb, console, sleep, fetch,
    get_client_id, exec, Date,
)


def test_dom_find_raises():
    with pytest.raises(ClientOnlyError):
        DOM.find("my-id")


def test_dom_create_raises():
    with pytest.raises(ClientOnlyError):
        DOM.create("div")


def test_storage_get_raises():
    with pytest.raises(ClientOnlyError):
        localStorage.get("key")


def test_storage_set_raises():
    with pytest.raises(ClientOnlyError):
        localStorage.set("key", "value")


def test_storage_getattr_raises():
    with pytest.raises(ClientOnlyError):
        _ = localStorage.foo


def test_sleep_raises():
    import asyncio
    with pytest.raises(ClientOnlyError):
        asyncio.get_event_loop().run_until_complete(sleep(1))


def test_get_client_id_raises():
    with pytest.raises(ClientOnlyError):
        get_client_id()


def test_console_log_raises():
    with pytest.raises(ClientOnlyError):
        console.log("hello")


def test_exec_raises():
    with pytest.raises(ClientOnlyError):
        exec("window.thing()")


def test_date_now_raises():
    with pytest.raises(ClientOnlyError):
        Date.now()


def test_idb_get_raises():
    import asyncio
    with pytest.raises(ClientOnlyError):
        asyncio.get_event_loop().run_until_complete(idb.get("key"))
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tests/test_js_shims.py -v
```
Expected: all 11 tests PASS.

- [ ] **Step 4: Format and commit**

```bash
uv run ruff format violetear/js.py tests/test_js_shims.py
git add violetear/js.py tests/test_js_shims.py
git commit -m "feat(js): violetear.js browser API shims with ClientOnlyError"
```

---

### Task 4: `violetear/runtime.js` — vanilla JS runtime

**Files:**
- Create: `violetear/runtime.js`

**Interfaces:**
- Produces globals: `ReactiveRegistry`, `DOM`, `DOMElement`, `Storage`, `IDBStore`, `sleep`, `get_client_id`, `exec`, `console` (native), `fetch` (native), `Date` (native), `localStorage` (wrapped), `sessionStorage` (wrapped), `idb`
- Produces entry point: `Violetear_hydrate(scope)`

- [ ] **Step 1: Create `violetear/runtime.js`**

```javascript
// violetear runtime.js — replaces the Pyodide-side Python bundle.
// Loaded as <script src="/_violetear/runtime.js"> before bundle.js.
// Defines globals that compiled bundle code references directly.
"use strict";

// ---------------------------------------------------------------------------
// ReactiveRegistry — pub/sub for @app.local state
// ---------------------------------------------------------------------------
const ReactiveRegistry = (() => {
  const _subs = {}; // path -> { id -> callback }
  let _counter = 0;
  return {
    notify(path, value) {
      const bucket = _subs[path];
      if (!bucket) return;
      for (const cb of Object.values(bucket)) {
        try { cb(value); } catch (e) { console.error("[violetear] reactive update error:", e); }
      }
    },
    bind(path, callback) {
      if (!_subs[path]) _subs[path] = {};
      const id = _counter++;
      _subs[path][id] = callback;
      return () => { if (_subs[path]) delete _subs[path][id]; };
    },
  };
})();

// ---------------------------------------------------------------------------
// DOMElement — wraps a native browser element
// ---------------------------------------------------------------------------
class DOMElement {
  constructor(el) { this._el = el; }

  get text() { return this._el ? this._el.innerText : ""; }
  set text(v) { if (this._el) this._el.innerText = String(v); }

  get html() { return this._el ? this._el.innerHTML : ""; }
  set html(v) { if (this._el) this._el.innerHTML = String(v); }

  get value() { return this._el ? this._el.value : undefined; }
  set value(v) { if (this._el) this._el.value = String(v); }

  add(...classes) { classes.forEach(c => this._el && this._el.classList.add(c)); return this; }
  remove(...classes) { classes.forEach(c => this._el && this._el.classList.remove(c)); return this; }
  toggle(cls, force) {
    if (!this._el) return this;
    if (force === true) this._el.classList.add(cls);
    else if (force === false) this._el.classList.remove(cls);
    else this._el.classList.toggle(cls);
    return this;
  }
  append(child) { if (this._el && child._el) this._el.appendChild(child._el); return this; }
  attr(name, value) {
    if (!this._el) return value !== undefined ? this : null;
    if (value === undefined) return this._el.getAttribute(name);
    this._el.setAttribute(name, String(value));
    return this;
  }
  on(event, handler) { if (this._el) this._el.addEventListener(event, handler); return this; }
  query(selector) {
    if (!this._el) return [];
    return Array.from(this._el.querySelectorAll(selector)).map(e => new DOMElement(e));
  }
}

// ---------------------------------------------------------------------------
// DOM — static factory
// ---------------------------------------------------------------------------
const DOM = {
  find(id) { return new DOMElement(document.getElementById(id)); },
  create(tag) { return new DOMElement(document.createElement(tag)); },
  query(selector) { return Array.from(document.querySelectorAll(selector)).map(e => new DOMElement(e)); },
  body() { return new DOMElement(document.body); },
};

// ---------------------------------------------------------------------------
// Storage — JSON-transparent wrapper with namespacing
// ---------------------------------------------------------------------------
class _Storage {
  constructor(backend, prefix) {
    this._backend = backend;
    this._prefix = prefix ? prefix + ":" : "";
  }
  _k(key) { return this._prefix + key; }
  get(key, def = null) {
    const raw = this._backend.getItem(this._k(key));
    if (raw === null) return def;
    try { return JSON.parse(raw); } catch { return raw; }
  }
  set(key, value) { this._backend.setItem(this._k(key), JSON.stringify(value)); }
  remove(key) { this._backend.removeItem(this._k(key)); }
  has(key) { return this._backend.getItem(this._k(key)) !== null; }
  clear() {
    const prefix = this._prefix;
    Object.keys(this._backend)
      .filter(k => k.startsWith(prefix))
      .forEach(k => this._backend.removeItem(k));
  }
}

// Proxy enables attribute-style access: localStorage.foo = bar
function _makeStorage(backend, prefix) {
  const store = new _Storage(backend, prefix);
  return new Proxy(store, {
    get(t, prop) {
      if (prop in t || typeof prop === "symbol") return t[prop];
      return t.get(prop);
    },
    set(t, prop, value) {
      if (prop.startsWith("_")) { t[prop] = value; return true; }
      t.set(prop, value);
      return true;
    },
  });
}

// Placeholder — overwritten by Violetear_hydrate with the app's prefix
let localStorage = _makeStorage(window.localStorage, "");
let sessionStorage = _makeStorage(window.sessionStorage, "");

// ---------------------------------------------------------------------------
// IDBStore — async KV backed by IndexedDB
// ---------------------------------------------------------------------------
class IDBStore {
  constructor(dbName) {
    this._dbName = dbName;
    this._db = null;
  }
  async _open() {
    if (this._db) return this._db;
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(this._dbName, 1);
      req.onupgradeneeded = e => e.target.result.createObjectStore("kv");
      req.onsuccess = e => { this._db = e.target.result; resolve(this._db); };
      req.onerror = e => reject(e.target.error);
    });
  }
  async _tx(mode, fn) {
    const db = await this._open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction("kv", mode);
      const store = tx.objectStore("kv");
      const req = fn(store);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }
  async get(key, def = null) {
    const raw = await this._tx("readonly", s => s.get(key));
    if (raw === undefined) return def;
    return raw;
  }
  async set(key, value) { await this._tx("readwrite", s => s.put(value, key)); }
  async remove(key) { await this._tx("readwrite", s => s.delete(key)); }
  async has(key) { return (await this._tx("readonly", s => s.getKey(key))) !== undefined; }
  async keys() { return this._tx("readonly", s => s.getAllKeys()); }
  async items() {
    const db = await this._open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction("kv", "readonly");
      const store = tx.objectStore("kv");
      const result = [];
      store.openCursor().onsuccess = e => {
        const cursor = e.target.result;
        if (cursor) { result.push([cursor.key, cursor.value]); cursor.continue(); }
        else resolve(result);
      };
    });
  }
  async clear() { await this._tx("readwrite", s => s.clear()); }
}

let idb = new IDBStore("");

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------
function sleep(seconds) { return new Promise(r => setTimeout(r, seconds * 1000)); }

const _CLIENT_ID = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2);
function get_client_id() { return _CLIENT_ID; }

function exec(js_code) { eval(js_code); } // eslint-disable-line no-eval

// ---------------------------------------------------------------------------
// Hydration — events, reactive bindings, WebSocket
// ---------------------------------------------------------------------------
function _hydrate_events(scope) {
  document.querySelectorAll("*").forEach(el => {
    for (const attr of Array.from(el.attributes)) {
      if (attr.name.startsWith("data-on-")) {
        const event = attr.name.slice(8);
        const fn_name = attr.value;
        const fn = scope[fn_name];
        if (fn) el.addEventListener(event, fn);
        else console.warn(`[violetear] handler not found: ${fn_name}`);
      }
    }
  });
}

function _hydrate_bindings() {
  document.querySelectorAll("*").forEach(el => {
    for (const attr of Array.from(el.attributes)) {
      if (!attr.name.startsWith("data-bind-")) continue;
      const prop = attr.name.slice(10); // e.g. "text", "value", "class"
      const path = attr.value;          // e.g. "UiState.mode"
      let updater;
      if (prop === "text") updater = v => { el.innerText = String(v); };
      else if (prop === "html") updater = v => { el.innerHTML = String(v); };
      else if (prop === "value") updater = v => { el.value = String(v); };
      else if (prop === "class") updater = v => { el.className = String(v); };
      else updater = v => {
        if (v === false || v === null) el.removeAttribute(prop);
        else el.setAttribute(prop, String(v));
      };
      ReactiveRegistry.bind(path, updater);
    }
  });
}

let _violetear_socket = null;

function _setup_websocket(scope) {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const url = `${protocol}://${location.host}/_violetear/ws?client_id=${_CLIENT_ID}`;
  const socket = new WebSocket(url);
  _violetear_socket = socket;
  window.violetear_socket = socket;

  socket.onopen = () => {
    const handlers = scope._lifecycle?.connect ?? [];
    handlers.forEach(fn => fn().catch(e => console.error("[violetear] connect handler error:", e)));
  };

  socket.onmessage = event => {
    let data;
    try { data = JSON.parse(event.data); } catch { return; }
    if (data.type === "rpc") {
      const fn = scope[data.func];
      if (fn) fn(data.kwargs ?? {}).catch(e => console.error(`[violetear] rpc error in ${data.func}:`, e));
      else console.warn(`[violetear] rpc handler not found: ${data.func}`);
    }
  };

  socket.onclose = () => {
    const handlers = scope._lifecycle?.disconnect ?? [];
    handlers.forEach(fn => fn().catch(() => {}));
    setTimeout(() => _setup_websocket(scope), 3000);
  };
}

async function _dispatch_ready(scope) {
  const handlers = scope._lifecycle?.ready ?? [];
  for (const fn of handlers) {
    try { await fn(); } catch (e) { console.error("[violetear] ready handler error:", e); }
  }
}

// ---------------------------------------------------------------------------
// Entry point — called at end of bundle.js
// ---------------------------------------------------------------------------
async function Violetear_hydrate(scope, opts = {}) {
  // Apply storage prefix (namespacing)
  const prefix = opts.storage_prefix ?? "";
  localStorage = _makeStorage(window.localStorage, prefix);
  sessionStorage = _makeStorage(window.sessionStorage, prefix);
  idb = new IDBStore(prefix ? `violetear:${prefix}` : "violetear");

  _hydrate_events(scope);
  _hydrate_bindings();

  const needs_websocket = Object.keys(scope).some(k => !k.startsWith("_"));
  if (needs_websocket) _setup_websocket(scope);

  await _dispatch_ready(scope);
}
```

- [ ] **Step 2: No Python tests for runtime.js** — it will be validated end-to-end via playwright in Task 8. Verify the file is syntactically valid JS:

```bash
node --check violetear/runtime.js
```
Expected: no output (success).

- [ ] **Step 3: Commit**

```bash
git add violetear/runtime.js
git commit -m "feat(runtime): vanilla JS runtime — ReactiveRegistry, DOM, storage, WebSocket, hydration"
```

---

### Task 5: `violetear/app.py` — rewire to compiler + new endpoints

**Files:**
- Modify: `violetear/app.py`
- Modify: `tests/test_unit.py`
- Modify: `tests/test_examples_canonical.py`

**Interfaces:**
- Consumes: `transpile_class`, `transpile_function` from `violetear/transpile.py`
- Consumes: `violetear/runtime.js` (static file)
- Produces: `GET /_violetear/runtime.js`, `GET /_violetear/bundle.js`, updated `_inject_client_side`

- [ ] **Step 1: Remove Pyodide machinery from `violetear/app.py`**

Remove these sections entirely:
- Lines with `PYODIDE_VERSION`, `PYODIDE_FILES`, `PYODIDE_CDN_BASE` constants
- `_pyodide_cache_dir()` function
- `_ensure_pyodide_cached()` function
- `_pyodide_download_lock = threading.Lock()`
- The `GET /_violetear/pyodide/{filename:path}` route and its handler

Also remove the `urllib.request` import (no longer needed).

- [ ] **Step 2: Add new routes and update `ClientRegistry` in `violetear/app.py`**

In `App.__init__`, replace the `GET /_violetear/bundle.py` route with:

```python
from pathlib import Path as _Path
from violetear.transpile import transpile_class, transpile_function, ClientCompileError

# Serve static runtime.js
_runtime_js_path = _Path(__file__).parent / "runtime.js"

@self.api.get("/_violetear/runtime.js")
def get_runtime():
    return Response(
        content=_runtime_js_path.read_text(encoding="utf-8"),
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=3600"},
    )

@self.api.get("/_violetear/bundle.js")
def get_bundle():
    return Response(
        content=self._generate_bundle_js(),
        media_type="application/javascript",
    )
```

Update `App.local` to compile at decoration time:

```python
def local[T](self, cls: type[T]) -> T:
    # Compile to JS at decoration time — fail fast on unsupported constructs
    js = transpile_class(cls)
    self.client._compiled_classes[cls.__name__] = js
    # Keep server-side reactive proxy (used for SSR initial values)
    return local(cls)
```

Add `_compiled_classes: dict[str, str]` and `_compiled_functions: dict[str, list[tuple[str, str]]]` to `ClientRegistry.__init__`:

```python
class ClientRegistry:
    def __init__(self, app):
        self._app = app
        self._compiled_classes: dict[str, str] = {}
        # func_name -> (decorator_kind, js_source)
        # decorator_kind: "callback" | "realtime" | "on:<event>" | "client"
        self._compiled_functions: dict[str, tuple[str, str]] = {}
        self._lifecycle: dict[str, list[str]] = {}  # event -> [fn_name, ...]
```

Update `ClientRegistry.callback`, `ClientRegistry.realtime`, `ClientRegistry.on`, and the bare `@app.client` decorator to call `transpile_function(fn)` and store in `_compiled_functions`.

For `@app.client.on(event)`:
```python
def on(self, event: str):
    def decorator(fn):
        js = transpile_function(fn)
        self._compiled_functions[fn.__name__] = ("on:" + event, js)
        self._lifecycle.setdefault(event, []).append(fn.__name__)
        # Return a stub that raises server-side
        ...
    return decorator
```

For `@app.client.realtime`:
```python
def realtime(self, fn):
    js = transpile_function(fn)
    self._compiled_functions[fn.__name__] = ("realtime", js)
    # Realtime functions use destructured kwargs — rewrite param list
    # The server calls fn(kwargs), so JS receives {param1: v1, ...}
    # The compiled function signature becomes ({param1, param2})
    ...
```

**Note on realtime destructuring:** `@app.client.realtime` functions receive a single object from the runtime (`fn(data.kwargs)`). The compiler generates positional params, but for realtime handlers the runtime must call `fn(data.kwargs)` and the compiled function must accept it. Implement by wrapping the compiled output:

```python
def _wrap_realtime_params(fn_name: str, params: list[str], body: str) -> str:
    """Wrap realtime function to accept a kwargs object from the WS runtime."""
    # Original: async function receive_message(msg) { ... }
    # Wrapped:  async function receive_message({msg}) { ... }
    if not params:
        return f"async function {fn_name}() {{\n{body}\n}}"
    destructured = ", ".join(params)
    return f"async function {fn_name}({{{destructured}}}) {{\n{body}\n}}"
```

- [ ] **Step 3: Implement `_generate_bundle_js`**

```python
def _generate_bundle_js(self) -> str:
    """Generate bundle.js: compiled state classes + functions + RPC stubs + hydrate call."""
    parts: list[str] = []

    # 1. Compiled state classes
    for js in self.client._compiled_classes.values():
        parts.append(js)

    # 2. Compiled client functions
    for fn_name, (kind, js) in self.client._compiled_functions.items():
        parts.append(js)

    # 3. JS RPC stubs for @app.server.rpc
    for name, func in self.server.rpc_functions.items():
        sig = inspect.signature(func)
        params = [p.name for p in sig.parameters.values()
                  if p.name != "client_id"]
        param_str = ", ".join(params)
        destructured = ", ".join(params)
        parts.append(
            f"async function {name}({{{destructured}}}) {{\n"
            f'  const r = await fetch("/_violetear/rpc/{name}", {{\n'
            f'    method: "POST",\n'
            f'    headers: {{"Content-Type": "application/json"}},\n'
            f"    body: JSON.stringify({{{param_str}}})\n"
            f"  }});\n"
            f'  if (!r.ok) throw new Error(`RPC error: ${{r.status}}`);\n'
            f"  return r.json();\n"
            f"}}"
        )

    # 4. JS realtime stubs for @app.server.realtime
    for name, func in self.server.realtime_functions.items():
        sig = inspect.signature(func)
        params = [p.name for p in sig.parameters.values()
                  if p.name != "client_id"]
        param_str = ", ".join(params)
        destructured = ", ".join(params)
        parts.append(
            f"async function {name}({{{destructured}}}) {{\n"
            f"  window.violetear_socket.send(JSON.stringify({{\n"
            f'    type: "realtime", func: "{name}",\n'
            f"    args: [], kwargs: {{{param_str}}}\n"
            f"  }}));\n"
            f"}}"
        )

    # 5. Scope object + hydrate call
    # Group by decorator kind for lifecycle dispatch
    lifecycle_entries: list[str] = []
    for event, fn_names in self.client._lifecycle.items():
        names_js = ", ".join(fn_names)
        lifecycle_entries.append(f'    {event}: [{names_js}]')

    # Non-lifecycle scope entries (callable by name from WS/DOM)
    scope_entries: list[str] = []
    for fn_name in self.client._compiled_functions:
        scope_entries.append(f"  {fn_name}")

    lifecycle_block = ",\n".join(lifecycle_entries)
    scope_block = ",\n".join(scope_entries)

    storage_prefix = getattr(self, "storage_prefix", "") or self.title.lower().replace(" ", "-")

    parts.append(
        f"const _scope = {{\n"
        f"  _lifecycle: {{\n{lifecycle_block}\n  }},\n"
        f"{scope_block}\n"
        f"}};\n"
        f'Violetear_hydrate(_scope, {{ storage_prefix: "{storage_prefix}" }});'
    )

    return "\n\n".join(parts)
```

- [ ] **Step 4: Update `_inject_client_side` in `violetear/app.py`**

Replace the existing Pyodide injection with:

```python
def _inject_client_side(self, doc: Document):
    """Inject the JS runtime and compiled bundle into the document."""
    if self.fade_in > 0:
        cloak_script = (
            'var cloak = document.createElement("style");'
            'cloak.id = "violetear-cloak";'
            'cloak.innerHTML = "body { opacity: 0; pointer-events: none; }";'
            'document.head.appendChild(cloak);'
        )
        doc.script(content=cloak_script)

    doc.script(src="/_violetear/runtime.js")
    bundle_url = self._version_url("/_violetear/bundle.js")
    doc.script(src=bundle_url, defer=True)

    if self.fade_in > 0:
        # Fade in after bundle loads — bundle.js calls Violetear_hydrate synchronously
        # so cloak removal can happen at end of bundle evaluation
        fade_ms = int(self.fade_in * 1000)
        fade_script = (
            f'document.addEventListener("DOMContentLoaded", () => {{'
            f'  const cloak = document.getElementById("violetear-cloak");'
            f'  if (cloak) {{'
            f'    cloak.innerHTML = "body {{ opacity: 1; pointer-events: auto; '
            f'transition: opacity {self.fade_in}s ease-in-out; }}";'
            f'    setTimeout(() => cloak.remove(), {fade_ms});'
            f'  }}'
            f'}});'
        )
        doc.script(content=fade_script)
```

Also add `storage_prefix: str = ""` to `App.__init__` signature.

- [ ] **Step 5: Update `tests/test_examples_canonical.py`** — replace `bundle.py` references with `bundle.js`:

```python
# Change any assertion like:
assert "/_violetear/bundle.py" in html
# to:
assert "/_violetear/bundle.js" in html
```

Search for all occurrences:
```bash
grep -n "bundle.py" tests/test_examples_canonical.py
```
Update each one.

- [ ] **Step 6: Run unit tests**

```bash
uv run pytest tests/test_unit.py tests/test_examples_canonical.py tests/test_state.py -v
```
Expected: all PASS. Fix any failures before committing.

- [ ] **Step 7: Format and commit**

```bash
uv run ruff format violetear/app.py tests/test_unit.py tests/test_examples_canonical.py
git add violetear/app.py tests/test_unit.py tests/test_examples_canonical.py
git commit -m "feat(app): wire Python→JS compiler, remove Pyodide, add bundle.js + runtime.js routes"
```

---

### Task 6: Delete old files + update remaining tests

**Files:**
- Delete: `violetear/client.py`, `violetear/dom.py`, `violetear/storage.py`
- Modify: `tests/test_unit.py` (remove any remaining references to deleted modules)
- Modify: `tests/test_examples_canonical.py` (remove Pyodide bundle references)

- [ ] **Step 1: Delete the three old modules**

```bash
git rm violetear/client.py violetear/dom.py violetear/storage.py
```

- [ ] **Step 2: Search for any remaining imports of deleted modules**

```bash
grep -rn "from violetear.client\|from violetear.dom\|from violetear.storage\|import client\|import dom\|import storage" violetear/ tests/ examples/
```

Fix any imports found (they must not remain in framework code).

- [ ] **Step 3: Run full test suite**

```bash
uv run pytest tests --cov=violetear -v
```
Expected: all pass. If `test_unit.py` has tests that import deleted modules, remove those tests. The stubs-raise semantics are now covered by `test_js_shims.py`.

- [ ] **Step 4: Format and commit**

```bash
uv run ruff format tests/
git add -A
git commit -m "chore: delete client.py, dom.py, storage.py — replaced by js.py + runtime.js"
```

---

### Task 7: Update examples 03, 04, 05

**Files:**
- Modify: `examples/03_interactive.py`
- Modify: `examples/04_pwa.py`
- Modify: `examples/05_realtime.py`

- [ ] **Step 1: Update `examples/03_interactive.py`**

Replace:
```python
from violetear.dom import Event
from violetear.storage import store
```
With:
```python
from violetear.js import Event, localStorage
```

Replace all `store.X` with `localStorage.X`.

Remove any `import asyncio` (there are none in 03, but double-check).

- [ ] **Step 2: Update `examples/04_pwa.py`**

Replace:
```python
from violetear.dom import Event
from violetear.pwa import Manifest
from violetear.storage import store
```
With:
```python
from violetear.js import Event, localStorage, sleep
from violetear.pwa import Manifest
```

Replace all `store.X` with `localStorage.X`.

Inside `tick()`: remove `import asyncio` and replace `await asyncio.sleep(1)` with `await sleep(1)`.

- [ ] **Step 3: Update `examples/05_realtime.py`**

Replace:
```python
from violetear.dom import DOM, Event
```
With:
```python
from violetear.js import DOM, Event, get_client_id
```

Remove `from violetear.client import get_client_id` from all function bodies (it's now a top-level import).

- [ ] **Step 4: Run canonical tests**

```bash
uv run pytest tests/test_examples_canonical.py -v
```
Expected: all PASS.

- [ ] **Step 5: Run full test suite**

```bash
make test-unit
```
Expected: format-check PASS, all tests PASS.

- [ ] **Step 6: Format and commit**

```bash
uv run ruff format examples/03_interactive.py examples/04_pwa.py examples/05_realtime.py
git add examples/03_interactive.py examples/04_pwa.py examples/05_realtime.py
git commit -m "feat(examples): update 03/04/05 to violetear.js imports, remove Pyodide patterns"
```

---

### Task 8: End-to-end verification + version bump

**Files:**
- Modify: `pyproject.toml`
- Modify: `violetear/__init__.py`
- Modify: `roadmap.md`

- [ ] **Step 1: Run e2e tests against examples 03, 04, 05**

```bash
make e2e
```
Expected: all Playwright browser tests PASS. These exercise real DOM hydration, WebSocket, and reactive bindings in Chromium.

If e2e tests fail, debug against the running app:
```bash
python examples/03_interactive.py &
# open http://localhost:8000 in browser
# check browser console for JS errors
# check Network tab for bundle.js content
```

- [ ] **Step 2: Manual smoke test for each interactive example**

```bash
python examples/03_interactive.py
# http://localhost:8000 — edit meters/feet/inches fields, verify live updates
# Toggle quick/precise mode, verify RPC path works
# Refresh page, verify localStorage restore

python examples/04_pwa.py
# http://localhost:8000 — click Start, verify timer counts down
# Click Pause, click Reset, switch modes
# Refresh, verify timer state restores from localStorage

python examples/05_realtime.py
# http://localhost:8000 in two tabs
# Send a message — verify it appears in both tabs
# Rename — verify user list updates in both tabs
```

- [ ] **Step 3: Update `roadmap.md`**

Mark Phase 1 through 4 complete and add a Phase 5 entry:

```markdown
## Phase 5: v2.0 — Python→JS Compiler (Complete)

- [x] **Remove Pyodide**: replaced with `runtime.js` (~400 lines vanilla JS)
- [x] **`transpile.py`**: Python→JS AST compiler for state classes and client functions
- [x] **`violetear/js.py`**: browser API shims for IDE/mypy support
- [x] **`violetear/runtime.js`**: ReactiveRegistry, hydration, WebSocket, DOM, Storage, IDB
- [x] **Updated examples**: 03/04/05 use `from violetear.js import ...`
```

- [ ] **Step 4: Version bump to 2.0.0**

```bash
NEW_VERSION=2.0.0 make release
```

This runs format-check, full test suite, bumps both version files, commits, tags `v2.0.0`, pushes, and creates the GitHub release.

Expected output ends with: `✅ Version 2.0.0 successfully released.`
