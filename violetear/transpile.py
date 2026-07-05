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
        head = (
            f"{self.filename}:{self.line}:{self.col}: {self.category}: {self.message}"
        )
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
            f"this._{f.name} = v; "
            f'ReactiveRegistry.notify("{class_name}.{f.name}", v); }}'
        )

    lines.append("}")
    lines.append(f"const {class_name} = new _{class_name}();")
    return "\n".join(lines)
