# Semantic Soundness — Slice 3 (membership) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Support Python `in` / `not in` (currently a hard compile error) with correct runtime semantics for lists, strings, and dicts.

**Architecture:** Add `_py.contains(container, x)` to `runtime.js` (dispatches on container runtime type: string→substring, array→value membership via `_py.eq`, object→key membership). Wire `transpile.py` `ast.Compare` `In`/`NotIn`.

**Tech Stack:** Python 3.12+, pytest, node. No JS build tooling.

## Global Constraints

- No JS build tooling; `_py` is served JS. No new runtime dependency.
- `uv run ruff format` (not `make format`); work on `main`; conventional commits.
- Slice-3 scope: `in` / `not in` in expression/condition position. Array membership uses
  value equality (`_py.eq`) to match Python; dict membership is key membership.

---

### Task 1: `_py.contains`

**Files:** Modify `violetear/runtime.js`; extend `tests/test_py_runtime_e2e.py`.

**Interfaces:** Produces `_py.contains(c, x)` — `true`/`false` for membership.

- [ ] **Step 1: Extend the e2e** (append to `tests/test_py_runtime_e2e.py`)

```python
@pytest.mark.e2e
def test_py_contains(example_server, page):
    _boot(example_server, page)
    assert page.evaluate("() => _py.contains([1, 2, 3], 2)") is True
    assert page.evaluate("() => _py.contains([1, 2, 3], 9)") is False
    assert page.evaluate("() => _py.contains('hello', 'ell')") is True
    assert page.evaluate("() => _py.contains({a: 1, b: 2}, 'a')") is True
    assert page.evaluate("() => _py.contains({a: 1}, 'z')") is False
    assert page.evaluate("() => _py.contains([[1, 2]], [1, 2])") is True
```

- [ ] **Step 2: Implement** — add inside `const _py = { ... }` (after `str`, before closing `};`):

```javascript
  contains(c, x) {
    if (typeof c === "string") return c.includes(x);
    if (Array.isArray(c)) return c.some((e) => this.eq(e, x));
    if (c !== null && typeof c === "object") return Object.prototype.hasOwnProperty.call(c, x);
    return false;
  },
```

- [ ] **Step 3: Node-verify**

```bash
cd /home/apiad/Workspace/repos/violetear
node --check violetear/runtime.js && node --input-type=module -e "
import { readFileSync } from 'node:fs';
import assert from 'node:assert';
const rt = readFileSync('violetear/runtime.js','utf8');
const block = rt.slice(rt.indexOf('const _py = {'), rt.indexOf('// ReactiveRegistry'));
const _py = new Function(block + '\nreturn _py;')();
assert.equal(_py.contains([1,2,3], 2), true);
assert.equal(_py.contains([1,2,3], 9), false);
assert.equal(_py.contains('hello', 'ell'), true);
assert.equal(_py.contains({a:1,b:2}, 'a'), true);
assert.equal(_py.contains({a:1}, 'z'), false);
assert.equal(_py.contains([[1,2]], [1,2]), true);
console.log('ok - _py.contains verified');
"
```
Expected: `ok - _py.contains verified`.

- [ ] **Step 4: Commit**

```bash
cd /home/apiad/Workspace/repos/violetear
uv run ruff format tests/test_py_runtime_e2e.py
git add violetear/runtime.js tests/test_py_runtime_e2e.py
git commit -m "feat(runtime): _py.contains for Python in/not-in membership"
```

---

### Task 2: Transpiler wiring for `in` / `not in`

**Files:** Modify `violetear/transpile.py` (`_emit_expr` `ast.Compare`); Test `tests/test_transpile.py`.

**Interfaces:** Consumes `_py.contains`. Produces: `x in c` → `_py.contains(c, x)`; `x not in c` → `!_py.contains(c, x)`.

- [ ] **Step 1: Add failing tests** (append to `tests/test_transpile.py`)

```python
def test_transpile_in_uses_contains():
    async def fn(x, items):
        a = x in items
        b = x not in items

    js = transpile_function(fn)
    assert "_py.contains(items, x)" in js
    assert "!_py.contains(items, x)" in js


def test_transpile_in_condition():
    async def fn(key, d):
        if key in d:
            return

    js = transpile_function(fn)
    assert "_py.truthy(_py.contains(d, key))" in js
```

- [ ] **Step 2: Run — expect fail (currently raises ClientCompileError)**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_transpile.py -k "in_uses_contains or in_condition" -v`
Expected: FAIL — `ClientCompileError: unsupported comparison In`.

- [ ] **Step 3: Implement** in `violetear/transpile.py`.

In `_emit_expr`'s `ast.Compare` branch, after the `Eq`/`NotEq` intercepts and before `cmp_op = _CMP_OPS.get(type(op))`, add:

```python
        if isinstance(op, ast.In):
            return f"_py.contains({_emit_expr(comparator, ctx)}, {l})"
        if isinstance(op, ast.NotIn):
            return f"!_py.contains({_emit_expr(comparator, ctx)}, {l})"
```

- [ ] **Step 4: Run — expect pass**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_transpile.py -v`
Expected: all pass.

- [ ] **Step 5: Node-verify transpiled membership**

```bash
cd /home/apiad/Workspace/repos/violetear
cat > /home/apiad/Workspace/.playground/violetear-validators/mem_mod.py <<'PYX'
async def check(x, items, d):
    if x in items:
        return "in-list"
    if x not in d:
        return "not-in-dict"
    return "other"
PYX
uv run python - <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("mem_mod","/home/apiad/Workspace/.playground/violetear-validators/mem_mod.py")
m = importlib.util.module_from_spec(spec); sys.modules["mem_mod"]=m; spec.loader.exec_module(m)
from violetear.transpile import transpile_function
open('/home/apiad/Workspace/.playground/violetear-validators/mem.js','w').write(transpile_function(m.check))
PY
node --input-type=module -e "
import { readFileSync } from 'node:fs';
import assert from 'node:assert';
const rt = readFileSync('violetear/runtime.js','utf8');
const block = rt.slice(rt.indexOf('const _py = {'), rt.indexOf('// ReactiveRegistry'));
const fn = readFileSync('/home/apiad/Workspace/.playground/violetear-validators/mem.js','utf8');
const check = new Function(block + '\n' + fn + '\nreturn check;')();
assert.equal(await check(2, [1,2,3], {}), 'in-list');
assert.equal(await check('z', [1,2,3], {a:1}), 'not-in-dict');
assert.equal(await check('a', [1,2,3], {a:1}), 'other');
console.log('ok - transpiled in/not-in computes Python membership');
"
```
Expected: `ok - transpiled in/not-in computes Python membership`.

- [ ] **Step 6: Format + commit**

```bash
cd /home/apiad/Workspace/repos/violetear
uv run ruff format violetear/transpile.py tests/test_transpile.py
git add violetear/transpile.py tests/test_transpile.py
git commit -m "feat(transpile): Python in / not in via _py.contains"
```

---

### Task 3: Regression + roadmap

- [ ] **Step 1:** `cd /home/apiad/Workspace/repos/violetear && make` → exit 0. If any test asserted `in` raises, remove/replace it (it is now supported).
- [ ] **Step 2:** In `roadmap.md`, flip Phase 7 Slice 3 to `[x]` and mark Phase 7 (issue #9) complete for the planned scope.
- [ ] **Step 3:** Commit `docs(roadmap): issue #9 slice 3 — membership (in/not in)`.

## Self-Review

- **Coverage:** `in`/`not in` → Task 2; `_py.contains` (string/array/dict dispatch) → Task 1. Array membership uses `_py.eq` (value equality, matches Python).
- **Placeholders:** none.
- **Type consistency:** `_py.contains(c, x)` def (Task 1) matches emit `_py.contains(comparator, l)` (Task 2). Intercept placed alongside the slice-1 `Eq`/`NotEq` intercepts, before `_CMP_OPS`.
