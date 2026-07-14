# Semantic Soundness — Slice 1 (truthiness + equality + f-string format) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make the transpiler emit Python-correct semantics for truthiness, equality, and f-string format specs via a runtime `_py` helper.

**Architecture:** Add a zero-dep `const _py = {...}` to `runtime.js` (sibling to the `_check*` primitives) with `truthy`/`and`/`or`/`eq`/`ne`/`format`. Wire `transpile.py` to emit calls into it for `if`/`while`/ternary tests, `not`, `and`/`or`, `==`/`!=`, `bool()`, and constant f-string format specs.

**Tech Stack:** Python 3.12+, pytest, node (local JS verification), Playwright (browser e2e). No `node`/`tsc`/`esbuild` in the pipeline.

## Global Constraints

- No JS build tooling; `_py` is served JS like `runtime.js`. No new runtime dependency.
- Unsupported/computed cases fail loud or pass through as `String` — never a silent *different-wrong* result.
- `uv run ruff format` (not `make format`); work on `main`; conventional commits.
- Slice-1 scope: truthiness + equality + f-string format only. `%`, `*`, `+`, `len(dict)`, `str()`/`bool()`-on-collections (slice 2) and `in`/`not in` (slice 3) are OUT.
- Existing transpile tests that assert the old condition/eq strings are UPDATED to the new `_py.*` forms (characterization update, not regression).

---

### Task 1: The `_py` runtime helper

**Files:**
- Modify: `violetear/runtime.js` (insert `_py` after the `_check*` block, before `ReactiveRegistry`)
- Test: `tests/test_py_runtime_e2e.py`

**Interfaces:** Produces globals `_py.truthy(x)`, `_py.and(a, bf)`, `_py.or(a, bf)`, `_py.eq(a, b)`, `_py.ne(a, b)`, `_py.format(value, spec)`.

- [ ] **Step 1: Write the failing e2e** (`tests/test_py_runtime_e2e.py`)

```python
"""Exercise the runtime.js _py semantics helper in Chromium via Playwright.
Marked e2e (needs a browser); runs on a browser-equipped host. Navigates a
canonical example (runtime.js loaded as globals) rather than about:blank."""

import pytest

HYDRATION_TIMEOUT_MS = 45_000


def _boot(example_server, page):
    base = example_server("03_interactive.py")
    page.goto(base + "/")
    page.wait_for_function(
        "() => document.getElementById('violetear-cloak') === null",
        timeout=HYDRATION_TIMEOUT_MS,
    )


@pytest.mark.e2e
def test_py_truthy(example_server, page):
    _boot(example_server, page)
    assert page.evaluate("() => [_py.truthy([]), _py.truthy([1]), _py.truthy(0), "
                         "_py.truthy(''), _py.truthy({}), _py.truthy({a:1}), _py.truthy(false)]") \
        == [False, True, False, False, False, True, False]


@pytest.mark.e2e
def test_py_eq_and_shortcircuit(example_server, page):
    _boot(example_server, page)
    assert page.evaluate("() => _py.eq([1,2],[1,2])") is True
    assert page.evaluate("() => _py.eq({a:1},{a:1})") is True
    assert page.evaluate("() => _py.eq([1],[2])") is False
    assert page.evaluate("() => _py.or([], () => 5)") == 5
    assert page.evaluate("() => _py.and([1], () => 2)") == 2


@pytest.mark.e2e
def test_py_format(example_server, page):
    _boot(example_server, page)
    assert page.evaluate("() => _py.format(5, '02d')") == "05"
    assert page.evaluate("() => _py.format(3.14159, '.2f')") == "3.14"
    assert page.evaluate("() => _py.format(255, 'x')") == "ff"
```

- [ ] **Step 2: Run — expect fail**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_py_runtime_e2e.py -m e2e -v`
Expected: FAIL — `_py is not defined` (or, on a browser-less host, browser-launch error; if so, defer to Step 4's node verification which is authoritative locally).

- [ ] **Step 3: Implement** — insert after the `_validateKwargs` function (end of the `_check*` block) in `violetear/runtime.js`:

```javascript
// ---------------------------------------------------------------------------
// _py — Python semantics helpers the transpiler emits calls into.
// ---------------------------------------------------------------------------
const _py = {
  truthy(x) {
    if (typeof x === "boolean") return x;
    if (x === null || x === undefined) return false;
    if (typeof x === "number") return x !== 0;
    if (typeof x === "string") return x.length > 0;
    if (Array.isArray(x)) return x.length > 0;
    if (typeof x === "object") return Object.keys(x).length > 0;
    return true;
  },
  and(a, bf) { return this.truthy(a) ? bf() : a; },
  or(a, bf) { return this.truthy(a) ? a : bf(); },
  eq(a, b) {
    if (a === b) return true;
    if (a === null || b === null || a === undefined || b === undefined) return false;
    if (typeof a !== "object" || typeof b !== "object") return a === b;
    const aArr = Array.isArray(a), bArr = Array.isArray(b);
    if (aArr !== bArr) return false;
    if (aArr) {
      if (a.length !== b.length) return false;
      for (let i = 0; i < a.length; i++) if (!this.eq(a[i], b[i])) return false;
      return true;
    }
    const ka = Object.keys(a), kb = Object.keys(b);
    if (ka.length !== kb.length) return false;
    for (const k of ka) {
      if (!Object.prototype.hasOwnProperty.call(b, k)) return false;
      if (!this.eq(a[k], b[k])) return false;
    }
    return true;
  },
  ne(a, b) { return !this.eq(a, b); },
  format(value, spec) {
    const m = /^(0?)(\d*)(?:\.(\d+))?([a-zA-Z%]?)$/.exec(spec);
    if (!m) return String(value);
    const zero = m[1] === "0";
    const width = m[2] ? parseInt(m[2], 10) : 0;
    const prec = m[3] !== undefined ? parseInt(m[3], 10) : null;
    const type = m[4].toLowerCase();
    let s;
    if (type === "d") s = String(Math.trunc(Number(value)));
    else if (type === "f") s = Number(value).toFixed(prec === null ? 6 : prec);
    else if (type === "x") s = Math.trunc(Number(value)).toString(16);
    else if (type === "%") s = (Number(value) * 100).toFixed(prec === null ? 6 : prec) + "%";
    else if (prec !== null && typeof value === "string") s = value.slice(0, prec);
    else s = String(value);
    if (width > s.length) {
      const pad = width - s.length;
      if (type === "" || type === "s") {
        s = s + " ".repeat(pad);
      } else if (zero && (s[0] === "-" || s[0] === "+")) {
        s = s[0] + "0".repeat(pad) + s.slice(1);
      } else {
        s = (zero ? "0" : " ").repeat(pad) + s;
      }
    }
    return s;
  },
};
```

- [ ] **Step 4: Node-verify the `_py` block locally (authoritative on zion)**

```bash
cd /home/apiad/Workspace/repos/violetear
node --input-type=module -e "
import { readFileSync } from 'node:fs';
const rt = readFileSync('violetear/runtime.js','utf8');
const block = rt.slice(rt.indexOf('const _py = {'), rt.indexOf('// ReactiveRegistry'));
const _py = new Function(block + '\nreturn _py;')();
import assert from 'node:assert';
assert.deepEqual([_py.truthy([]),_py.truthy([1]),_py.truthy(0),_py.truthy(''),_py.truthy({}),_py.truthy({a:1})],[false,true,false,false,false,true]);
assert.equal(_py.eq([1,2],[1,2]), true);
assert.equal(_py.eq({a:1},{a:1}), true);
assert.equal(_py.eq([1],[2]), false);
assert.equal(_py.or([], () => 5), 5);
assert.equal(_py.and([1], () => 2), 2);
assert.equal(_py.format(5,'02d'), '05');
assert.equal(_py.format(3.14159,'.2f'), '3.14');
assert.equal(_py.format(255,'x'), 'ff');
assert.equal(_py.format(-5,'03d'), '-05');
console.log('ok - _py verified');
"
```
Expected: `ok - _py verified`.

- [ ] **Step 5: Commit**

```bash
cd /home/apiad/Workspace/repos/violetear
git add violetear/runtime.js tests/test_py_runtime_e2e.py
git commit -m "feat(runtime): _py Python-semantics helper (truthy/and/or/eq/ne/format)"
```

---

### Task 2: Transpiler wiring

**Files:**
- Modify: `violetear/transpile.py` (`_emit_stmt` If/While; `_emit_expr` IfExp/UnaryOp/BoolOp/Compare/JoinedStr; `_try_builtin` bool; add `_constant_format_spec` helper)
- Test: `tests/test_transpile.py` (add new cases; update 3 existing)

**Interfaces:** Consumes `_py.*` (Task 1). Produces: `if`/`while`/ternary tests wrapped in `_py.truthy(...)`; `not x` → `!_py.truthy(x)`; `a and b` → `_py.and(a, () => b)`; `a or b` → `_py.or(a, () => b)`; `x == y` → `_py.eq(x, y)`; `x != y` → `_py.ne(x, y)`; `bool(x)` → `_py.truthy(x)`; `f"{n:02d}"` → `` `${_py.format(n, "02d")}` ``.

- [ ] **Step 1: Add new failing tests + update the 3 that change** (`tests/test_transpile.py`)

Update these three existing tests to the new forms:

```python
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


def test_transpile_function_ternary():
    async def fn(x):
        y = "a" if x else "b"

    js = transpile_function(fn)
    assert '(_py.truthy(x) ? "a" : "b")' in js
```

Append new tests:

```python
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

    import pytest as _pytest
    with _pytest.raises(ClientCompileError, match="format spec"):
        transpile_function(fn)
```

- [ ] **Step 2: Run — expect failures**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_transpile.py -v`
Expected: the 3 updated + 7 new fail (old forms still emitted).

- [ ] **Step 3: Implement** in `violetear/transpile.py`.

In `_emit_stmt`, `ast.If` branch — wrap the test:

```python
    if isinstance(node, ast.If):
        cond = f"_py.truthy({_emit_expr(node.test, ctx)})"
```

`ast.While` branch:

```python
    if isinstance(node, ast.While):
        cond = f"_py.truthy({_emit_expr(node.test, ctx)})"
        body = _emit_block(node.body, ctx)
        return f"while ({cond}) {{\n{body}\n}}"
```

In `_emit_expr`, `ast.IfExp`:

```python
    if isinstance(node, ast.IfExp):
        cond = f"_py.truthy({_emit_expr(node.test, ctx)})"
        body = _emit_expr(node.body, ctx)
        orelse = _emit_expr(node.orelse, ctx)
        return f"({cond} ? {body} : {orelse})"
```

`ast.UnaryOp` / `ast.Not` case — replace `return f"(!{v})"`:

```python
        if isinstance(node.op, ast.Not):
            return f"!_py.truthy({v})"
```

`ast.BoolOp` — replace the whole branch:

```python
    if isinstance(node, ast.BoolOp):
        helper = "_py.and" if isinstance(node.op, ast.And) else "_py.or"
        vals = [_emit_expr(v, ctx) for v in node.values]
        expr = vals[-1]
        for v in reversed(vals[:-1]):
            expr = f"{helper}({v}, () => {expr})"
        return expr
```

`ast.Compare` — after the `is None` / `is not None` handling and before `cmp_op = _CMP_OPS.get(...)`, intercept Eq/NotEq:

```python
        if isinstance(op, ast.Eq):
            return f"_py.eq({l}, {_emit_expr(comparator, ctx)})"
        if isinstance(op, ast.NotEq):
            return f"_py.ne({l}, {_emit_expr(comparator, ctx)})"
```

`ast.JoinedStr` — handle a constant format_spec:

```python
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
```

Add the helper near the other module-level helpers (e.g. above `_emit_call`):

```python
def _constant_format_spec(fmt: ast.JoinedStr, ctx: _CompileContext, node: ast.expr) -> str:
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
```

In `_try_builtin`, `bool` case — replace:

```python
        case "bool":
            return f"_py.truthy({pos_args[0]})" if pos_args else "false"
```

- [ ] **Step 4: Run — expect pass**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_transpile.py -v`
Expected: all pass (updated 3 + new 7 + untouched rest). Note `test_transpile_function_is_none` still passes — `(x === null)` remains a substring inside the `_py.truthy(...)` wrap.

- [ ] **Step 5: Node-verify a transpiled snippet computes Python-correctly**

```bash
cd /home/apiad/Workspace/repos/violetear
uv run python - <<'PY'
from violetear.transpile import transpile_function
async def demo(items):
    if not items:
        return "empty"
    return f"{len(items):02d}"
print(transpile_function(demo))
PY
```
Expected output includes `!_py.truthy(items)` and `_py.format(...)`. (Runtime behavior of `len` is slice 2; this step just confirms the emitted forms.)

- [ ] **Step 6: Format + commit**

```bash
cd /home/apiad/Workspace/repos/violetear
uv run ruff format violetear/transpile.py tests/test_transpile.py
git add violetear/transpile.py tests/test_transpile.py
git commit -m "feat(transpile): Python truthiness, deep equality, f-string format via _py"
```

---

### Task 3: Regression + example check + roadmap

- [ ] **Step 1:** `cd /home/apiad/Workspace/repos/violetear && make` → exit 0 (all unit tests, incl. example-canonical bundle tests, green). If any non-transpile test asserted an old condition string, update it to the `_py` form.
- [ ] **Step 2:** Sanity-check example 04's f-string now emits `_py.format`:

```bash
cd /home/apiad/Workspace/repos/violetear
uv run python -c "
import importlib.util, sys
s = importlib.util.spec_from_file_location('e4','examples/04_pwa.py')
m = importlib.util.module_from_spec(s); sys.modules['e4']=m; s.loader.exec_module(m)
b = m.app._generate_bundle_js()
assert '_py.format(' in b, 'expected _py.format in example-04 bundle'
print('ok - example 04 time display now uses _py.format')
"
```

- [ ] **Step 3:** In `roadmap.md`, under Phase 6, flip the issue-9 line and add the slice list:

```markdown
- [~] **Issue #9**: semantic soundness of the transpiler.
  - [x] Slice 1: truthiness + equality + f-string format specs (`_py` runtime helper).
  - [ ] Slice 2: numeric/sequence (`%`, `*`, `+`, `len(dict)`, `str()`/`bool()` on collections).
  - [ ] Slice 3: membership (`in` / `not in`).
```

- [ ] **Step 4:** Commit `docs(roadmap): issue #9 slice 1 — semantic soundness (truthiness/eq/format)`.

## Self-Review

- **Coverage:** spec §4.1 `_py` helper → Task 1; spec §4.2 transpiler wiring (if/while/ternary/not/and/or/==/!=/bool/f-string) → Task 2; spec §4.3 test updates → Task 2 Step 1; §5 success criteria → Tasks 1 (node/e2e) + 2 (transpile asserts) + 3 (example check).
- **Placeholders:** none — full `_py` JS and every transpiler edit shown.
- **Type consistency:** `_py.truthy/and/or/eq/ne/format` names identical across Task 1 (def) and Task 2 (emit). Thunk form `() => b` matches `and(a, bf)`/`or(a, bf)`. `_constant_format_spec(fmt, ctx, node)` used only in Task 2. `is None` path untouched (keeps `=== null`).
