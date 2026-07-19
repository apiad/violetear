"""Python→JS AST compiler for violetear client-side code."""

from __future__ import annotations

import ast
import dataclasses
import inspect
import json
import textwrap
from typing import Any, get_type_hints

from .validate import js_type_check


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

    try:
        hints = get_type_hints(cls)
    except Exception:
        hints = {}

    for f in fields:
        ann = hints.get(f.name)
        checker = js_type_check(ann) if ann is not None else "_checkAny"
        lines.append(f"  get {f.name}() {{ return this._{f.name}; }}")
        lines.append(
            f"  set {f.name}(v) {{ "
            f'({checker})(v, "{class_name}.{f.name}"); '
            f"this._{f.name} = v; "
            f'ReactiveRegistry.notify("{class_name}.{f.name}", v); }}'
        )

    lines.append("}")
    lines.append(f"const {class_name} = new _{class_name}();")
    return "\n".join(lines)


_BIN_OPS: dict[type, str] = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.Mod: "%",
}

_AUG_OPS: dict[type, str] = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.Mod: "%",
}

_CMP_OPS: dict[type, str] = {
    ast.Eq: "===",
    ast.NotEq: "!==",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
}

_STRING_METHODS: dict[str, str] = {
    "strip": "trim",
    "upper": "toUpperCase",
    "lower": "toLowerCase",
    "startswith": "startsWith",
    "endswith": "endsWith",
    "split": "split",
}

_LIST_METHODS: dict[str, str] = {
    "append": "push",
    "pop": "pop",
    "reverse": "reverse",
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


def _collect_assigned_names(stmts: list[ast.stmt]) -> list[str]:
    """Return all plain-Name targets assigned in stmts (shallow + 1-level deep for if/while)."""
    names: list[str] = []
    for stmt in stmts:
        if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    names.append(t.id)
        elif isinstance(stmt, ast.If):
            names.extend(_collect_assigned_names(stmt.body))
            names.extend(_collect_assigned_names(stmt.orelse))
        elif isinstance(stmt, ast.While):
            names.extend(_collect_assigned_names(stmt.body))
    return names


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
                filename=ctx.filename,
                line=node.lineno,
                col=node.col_offset,
            )
        rhs = _emit_expr(node.value, ctx)
        lhs = ctx.declare(node.target.id)
        return f"{lhs} = {rhs};"

    if isinstance(node, ast.Assign):
        if len(node.targets) != 1:
            raise ClientCompileError(
                category="unsupported-construct",
                message="multi-target assignment (a = b = c) is not supported",
                filename=ctx.filename,
                line=node.lineno,
                col=node.col_offset,
            )
        target = node.targets[0]
        rhs = _emit_expr(node.value, ctx)
        return _emit_assignment_target(
            target, rhs, None, ctx, node.lineno, node.col_offset
        )

    if isinstance(node, ast.AugAssign):
        op = _AUG_OPS.get(type(node.op))
        if op is None:
            raise ClientCompileError(
                category="unsupported-construct",
                message=f"unsupported augmented operator {type(node.op).__name__}; "
                "use +, -, *, /, %",
                filename=ctx.filename,
                line=node.lineno,
                col=node.col_offset,
            )
        rhs = _emit_expr(node.value, ctx)
        return _emit_assignment_target(
            node.target, rhs, op, ctx, node.lineno, node.col_offset
        )

    if isinstance(node, ast.If):
        # Hoist any names first-declared inside any branch to outer scope.
        # JS `let` is block-scoped; Python if-branch variables are function-scoped.
        all_branch_stmts = list(node.body) + list(node.orelse)
        hoisted = [
            n
            for n in _collect_assigned_names(all_branch_stmts)
            if n not in ctx._declared
        ]
        # Deduplicate while preserving order
        seen: set[str] = set()
        hoisted_unique: list[str] = []
        for n in hoisted:
            if n not in seen:
                seen.add(n)
                hoisted_unique.append(n)
                ctx._declared.add(n)
        hoist_line = (
            ("let " + ", ".join(hoisted_unique) + ";\n") if hoisted_unique else ""
        )

        cond = f"_py.truthy({_emit_expr(node.test, ctx)})"
        body = _emit_block(node.body, ctx)
        out = f"{hoist_line}if ({cond}) {{\n{body}\n}}"
        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                elif_text = _emit_stmt(node.orelse[0], ctx)
                out += f" else {elif_text}"
            else:
                else_body = _emit_block(node.orelse, ctx)
                out += f" else {{\n{else_body}\n}}"
        return out

    if isinstance(node, ast.While):
        cond = f"_py.truthy({_emit_expr(node.test, ctx)})"
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
                filename=ctx.filename,
                line=node.lineno,
                col=node.col_offset,
            )
        # Pre-declare any names assigned inside the try body so they are
        # visible in the outer scope after the try/catch block (JS `let` is
        # block-scoped, so without this a variable assigned inside `try` would
        # raise ReferenceError when read in subsequent outer statements).
        hoisted: list[str] = []
        for stmt in node.body:
            if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = (
                    stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
                )
                for t in targets:
                    if isinstance(t, ast.Name) and t.id not in ctx._declared:
                        ctx._declared.add(t.id)
                        hoisted.append(t.id)
        hoist_line = ""
        if hoisted:
            hoist_line = "let " + ", ".join(hoisted) + ";\n"
        body = _emit_block(node.body, ctx)
        catch_body = _emit_block(node.handlers[0].body, ctx)
        return f"{hoist_line}try {{\n{body}\n}} catch(_e) {{\n{catch_body}\n}}"

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
    target: ast.expr,
    rhs: str,
    aug_op: str | None,
    ctx: _CompileContext,
    line: int,
    col: int,
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
        filename=ctx.filename,
        line=line,
        col=col,
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
                filename=ctx.filename,
                line=node.lineno,
                col=node.col_offset,
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
                filename=ctx.filename,
                line=node.lineno,
                col=node.col_offset,
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
                filename=ctx.filename,
                line=node.lineno,
                col=node.col_offset,
            )
        k = node.target.elts[0]
        v = node.target.elts[1]
        if not (isinstance(k, ast.Name) and isinstance(v, ast.Name)):
            raise ClientCompileError(
                category="unsupported-construct",
                message="for-items loop variables must be plain names",
                filename=ctx.filename,
                line=node.lineno,
                col=node.col_offset,
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
            filename=ctx.filename,
            line=node.lineno,
            col=node.col_offset,
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
            filename=ctx.filename,
            line=node.lineno,
            col=node.col_offset,
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
        # Negative integer literal — JS [−n] returns undefined; use .at().
        if (
            isinstance(slc, ast.UnaryOp)
            and isinstance(slc.op, ast.USub)
            and isinstance(slc.operand, ast.Constant)
            and isinstance(slc.operand.value, int)
        ):
            return f"{obj}.at(-{slc.operand.value})"
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
        # Python +/*/% differ from JS on sequences and negative modulo.
        if isinstance(node.op, ast.Add):
            return f"_py.add({l}, {r})"
        if isinstance(node.op, ast.Mult):
            return f"_py.mul({l}, {r})"
        if isinstance(node.op, ast.Mod):
            return f"_py.mod({l}, {r})"
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise ClientCompileError(
                category="unsupported-construct",
                message=f"unsupported binary operator {type(node.op).__name__}",
                filename=ctx.filename,
                line=node.lineno,
                col=node.col_offset,
            )
        return f"({l} {op} {r})"

    if isinstance(node, ast.UnaryOp):
        v = _emit_expr(node.operand, ctx)
        if isinstance(node.op, ast.USub):
            return f"(-{v})"
        if isinstance(node.op, ast.Not):
            return f"!_py.truthy({v})"
        if isinstance(node.op, ast.UAdd):
            return v
        raise ClientCompileError(
            category="unsupported-construct",
            message=f"unsupported unary operator {type(node.op).__name__}",
            filename=ctx.filename,
            line=node.lineno,
            col=node.col_offset,
        )

    if isinstance(node, ast.BoolOp):
        # Python and/or return an operand (not a bool) with Python truthiness.
        # Fold right with thunks to preserve short-circuit + single evaluation:
        #   a and b and c -> _py.and(a, () => _py.and(b, () => c))
        helper = "_py.and" if isinstance(node.op, ast.And) else "_py.or"
        vals = [_emit_expr(v, ctx) for v in node.values]
        expr = vals[-1]
        for v in reversed(vals[:-1]):
            expr = f"{helper}({v}, () => {expr})"
        return expr

    if isinstance(node, ast.Compare):
        if len(node.ops) != 1:
            raise ClientCompileError(
                category="unsupported-construct",
                message="chained comparisons not supported; use explicit and/or",
                filename=ctx.filename,
                line=node.lineno,
                col=node.col_offset,
            )
        l = _emit_expr(node.left, ctx)
        comparator = node.comparators[0]
        op = node.ops[0]
        # is None / is not None
        if (
            isinstance(op, ast.Is)
            and isinstance(comparator, ast.Constant)
            and comparator.value is None
        ):
            return f"({l} === null)"
        if (
            isinstance(op, ast.IsNot)
            and isinstance(comparator, ast.Constant)
            and comparator.value is None
        ):
            return f"({l} !== null)"
        # Python == / != are value equality (deep for collections); JS === is
        # reference equality. Route through _py.eq / _py.ne.
        if isinstance(op, ast.Eq):
            return f"_py.eq({l}, {_emit_expr(comparator, ctx)})"
        if isinstance(op, ast.NotEq):
            return f"_py.ne({l}, {_emit_expr(comparator, ctx)})"
        # Python membership: x in c / x not in c (list/str/dict dispatch at runtime).
        if isinstance(op, ast.In):
            return f"_py.contains({_emit_expr(comparator, ctx)}, {l})"
        if isinstance(op, ast.NotIn):
            return f"!_py.contains({_emit_expr(comparator, ctx)}, {l})"
        cmp_op = _CMP_OPS.get(type(op))
        if cmp_op is None:
            raise ClientCompileError(
                category="unsupported-construct",
                message=f"unsupported comparison {type(op).__name__}; "
                "use ==, !=, <, <=, >, >= or 'is None' / 'is not None'",
                filename=ctx.filename,
                line=node.lineno,
                col=node.col_offset,
            )
        r = _emit_expr(comparator, ctx)
        return f"({l} {cmp_op} {r})"

    if isinstance(node, ast.IfExp):
        cond = f"_py.truthy({_emit_expr(node.test, ctx)})"
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
                if val.format_spec is not None:
                    spec = _constant_format_spec(val.format_spec, ctx, node)
                    parts.append(f"${{_py.format({expr}, {json.dumps(spec)})}}")
                else:
                    parts.append(f"${{{expr}}}")
            else:
                raise ClientCompileError(
                    category="unsupported-construct",
                    message="unsupported f-string component",
                    filename=ctx.filename,
                    line=node.lineno,
                    col=node.col_offset,
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


def _constant_format_spec(
    fmt: ast.JoinedStr, ctx: _CompileContext, node: ast.expr
) -> str:
    """Extract a constant f-string format spec (e.g. '02d'); raise on a computed one."""
    if (
        len(fmt.values) == 1
        and isinstance(fmt.values[0], ast.Constant)
        and isinstance(fmt.values[0].value, str)
    ):
        return fmt.values[0].value
    raise ClientCompileError(
        category="unsupported-construct",
        message="computed f-string format spec is not supported; use a constant like f'{x:02d}'",
        filename=ctx.filename,
        line=getattr(node, "lineno", 0),
        col=getattr(node, "col_offset", 0),
    )


def _emit_call(node: ast.Call, ctx: _CompileContext) -> str:
    """Emit a JS call expression, handling builtin translations and kwargs."""
    pos_args = [_emit_expr(a, ctx) for a in node.args]
    kw_args = {kw.arg: _emit_expr(kw.value, ctx) for kw in node.keywords if kw.arg}

    # Mixed positional + keyword args: emit fn(pos..., {key: val, ...}).
    # This matches the JS options-object convention (e.g. fetch(url, {method, body})).
    func = node.func

    # Named function call
    if isinstance(func, ast.Name):
        fname = func.id
        if not (pos_args and kw_args):
            translated = _try_builtin(fname, pos_args, kw_args, ctx, node)
            if translated is not None:
                return translated
        if kw_args:
            kw_str = ", ".join(f"{k}: {v}" for k, v in kw_args.items())
            all_args = pos_args + ["{" + kw_str + "}"]
            return f"{fname}({', '.join(all_args)})"
        return f"{fname}({', '.join(pos_args)})"

    # Method call
    if isinstance(func, ast.Attribute):
        obj = _emit_expr(func.value, ctx)
        method = func.attr

        # String method translations
        if method in _STRING_METHODS:
            js_method = _STRING_METHODS[method]
            return f"{obj}.{js_method}({', '.join(pos_args)})"

        # List method translations (append→push, pop, reverse)
        if method in _LIST_METHODS:
            js_method = _LIST_METHODS[method]
            return f"{obj}.{js_method}({', '.join(pos_args)})"

        # str.join(lst) — reversed receiver in JS: lst.join(sep)
        if method == "join" and pos_args:
            return f"{pos_args[0]}.join({obj})"

        if kw_args:
            kw_str = ", ".join(f"{k}: {v}" for k, v in kw_args.items())
            all_args = pos_args + ["{" + kw_str + "}"]
            return f"{obj}.{method}({', '.join(all_args)})"
        return f"{obj}.{method}({', '.join(pos_args)})"

    raise ClientCompileError(
        category="unsupported-construct",
        message=f"unsupported call form: {ast.unparse(node)!r}",
        filename=ctx.filename,
        line=node.lineno,
        col=node.col_offset,
    )


def _try_builtin(
    fname: str,
    pos_args: list[str],
    kw_args: dict[str, str],
    ctx: _CompileContext,
    node: ast.Call,
) -> str | None:
    """Return a JS translation for a recognized Python builtin, or None."""
    match fname:
        case "int":
            return f"Math.trunc(Number({pos_args[0]}))" if pos_args else "0"
        case "float":
            return f"Number({pos_args[0]})" if pos_args else "0.0"
        case "str":
            return f"_py.str({pos_args[0]})" if pos_args else '""'
        case "bool":
            return f"_py.truthy({pos_args[0]})" if pos_args else "false"
        case "len":
            return f"_py.len({pos_args[0]})"
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
                    filename=ctx.filename,
                    line=node.lineno,
                    col=node.col_offset,
                )
            return f"Math.min({pos_args[0]}, {pos_args[1]})"
        case "max":
            if len(pos_args) != 2:
                raise ClientCompileError(
                    category="unsupported-construct",
                    message="max() requires exactly 2 scalar arguments; list form not supported",
                    filename=ctx.filename,
                    line=node.lineno,
                    col=node.col_offset,
                )
            return f"Math.max({pos_args[0]}, {pos_args[1]})"
        case "pow":
            return f"Math.pow({pos_args[0]}, {pos_args[1]})"
        case "sum":
            raise ClientCompileError(
                category="unsupported-construct",
                message="sum() is not supported; use a for loop",
                filename=ctx.filename,
                line=node.lineno,
                col=node.col_offset,
            )
        case "isinstance":
            raise ClientCompileError(
                category="unsupported-construct",
                message="isinstance() is not supported in client code",
                filename=ctx.filename,
                line=node.lineno,
                col=node.col_offset,
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
