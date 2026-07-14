# Semantic Soundness — Slice 2 (numeric / sequence) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make `%`, `*`, `+`, `len()`, and `str()` compute Python semantics in the generated JS via the `_py` runtime helper.

**Architecture:** Extend the `_py` object in `runtime.js` with `mod`/`mul`/`add`/`len`/`str`/`repr`; wire `transpile.py` BinOp (`Add`→`_py.add`, `Mult`→`_py.mul`, `Mod`→`_py.mod`) and the `len`/`str` builtins.

**Tech Stack:** Python 3.12+, pytest, node (local JS verification). No JS build tooling.

## Global Constraints

- No JS build tooling; `_py` is served JS. No new runtime dependency.
- `uv run ruff format` (not `make format`); work on `main`; conventional commits.
- Slice-2 scope: `%`, `*`, `+`, `len()`, `str()` in **expression** position. Augmented
  assignment (`+=`/`*=`/`%=`) stays as JS operators (documented follow-up). `in`/`not in`
  is slice 3. `bool()` on collections was done in slice 1 (`bool()`→`_py.truthy`).
- `_py.str` implements a **Python-repr subset** (list/dict/bool/None + scalars); nested
  strings are quoted (repr), top-level strings are not. Deeper repr fidelity is out.

---

### Task 1: Extend `_py` with mod/mul/add/len/str/repr

**Files:** Modify `violetear/runtime.js`; extend `tests/test_py_runtime_e2e.py`.

**Interfaces:** Produces `_py.mod(a,b)`, `_py.mul(a,b)`, `_py.add(a,b)`, `_py.len(x)`, `_py.str(x)`, `_py.repr(x)`.

- [ ] **Step 1: Extend the e2e** (append cases to `tests/test_py_runtime_e2e.py`)

```python
@pytest.mark.e2e
def test_py_numeric_and_sequence(example_server, page):
    _boot(example_server, page)
    assert page.evaluate("() => _py.mod(-7, 3)") == 2          # floored modulo
    assert page.evaluate("() => _py.mul('a', 3)") == "aaa"      # string repeat
    assert page.evaluate("() => _py.mul([1, 2], 2)") == [1, 2, 1, 2]  # list repeat
    assert page.evaluate("() => _py.add([1], [2])") == [1, 2]   # list concat
    assert page.evaluate("() => _py.len({a: 1, b: 2})") == 2    # dict len
    assert page.evaluate("() => _py.str([1, 2])") == "[1, 2]"   # list str
```

- [ ] **Step 2: Implement** — add these methods inside the `const _py = { ... }` object in `violetear/runtime.js` (after `format`, before the closing `};`):

```javascript
  mod(a, b) { return ((a % b) + b) % b; },
  mul(a, b) {
    if (typeof a === "string" && typeof b === "number") return a.repeat(Math.max(0, b));
    if (typeof b === "string" && typeof a === "number") return b.repeat(Math.max(0, a));
    if (Array.isArray(a) && typeof b === "number") return Array.from({ length: Math.max(0, b) }, () => a).flat();
    if (Array.isArray(b) && typeof a === "number") return Array.from({ length: Math.max(0, a) }, () => b).flat();
    return a * b;
  },
  add(a, b) {
    if (Array.isArray(a) && Array.isArray(b)) return a.concat(b);
    return a + b;
  },
  len(x) {
    if (x === null || x === undefined) return 0;
    if (typeof x === "string" || Array.isArray(x)) return x.length;
    if (typeof x === "object") return Object.keys(x).length;
    return 0;
  },
  repr(x) {
    if (typeof x === "string") return "'" + x + "'";
    return this.str(x);
  },
  str(x) {
    if (x === true) return "True";
    if (x === false) return "False";
    if (x === null || x === undefined) return "None";
    if (Array.isArray(x)) return "[" + x.map((e) => this.repr(e)).join(", ") + "]";
    if (typeof x === "object") return "{" + Object.entries(x).map(([k, v]) => this.repr(k) + ": " + this.repr(v)).join(", ") + "}";
    return String(x);
  },
```

- [ ] **Step 3: Node-verify locally (authoritative on zion)**

```bash
cd /home/apiad/Workspace/repos/violetear
node --check violetear/runtime.js && node --input-type=module -e "
import { readFileSync } from 'node:fs';
import assert from 'node:assert';
const rt = readFileSync('violetear/runtime.js','utf8');
const block = rt.slice(rt.indexOf('const _py = {'), rt.indexOf('// ReactiveRegistry'));
const _py = new Function(block + '\nreturn _py;')();
assert.equal(_py.mod(-7,3), 2);
assert.equal(_py.mod(7,-3), -2);
assert.equal(_py.mul('a',3), 'aaa');
assert.deepEqual(_py.mul([1,2],2), [1,2,1,2]);
assert.equal(_py.mul(3,4), 12);
assert.deepEqual(_py.add([1],[2]), [1,2]);
assert.equal(_py.add(2,3), 5);
assert.equal(_py.len({a:1,b:2}), 2);
assert.equal(_py.len([1,2,3]), 3);
assert.equal(_py.str([1,2]), '[1, 2]');
assert.equal(_py.str(['a']), \"['a']\");
assert.equal(_py.str(true), 'True');
assert.equal(_py.str('hi'), 'hi');
console.log('ok - _py numeric/sequence verified');
"
```
Expected: `ok - _py numeric/sequence verified`.

- [ ] **Step 4: Commit**

```bash
cd /home/apiad/Workspace/repos/violetear
uv run ruff format tests/test_py_runtime_e2e.py
git add violetear/runtime.js tests/test_py_runtime_e2e.py
git commit -m "feat(runtime): _py mod/mul/add/len/str/repr (Python numeric+sequence)"
```

---

### Task 2: Transpiler wiring for `%`, `*`, `+`, `len`, `str`

**Files:** Modify `violetear/transpile.py` (`_emit_expr` BinOp; `_try_builtin` len/str); Test `tests/test_transpile.py` (add new; update 3 existing).

**Interfaces:** Consumes `_py.mod/mul/add/len/str`. Produces: `a % b`→`_py.mod(a, b)`; `a * b`→`_py.mul(a, b)`; `a + b`→`_py.add(a, b)`; `len(x)`→`_py.len(x)`; `str(x)`→`_py.str(x)`.

- [ ] **Step 1: Update the 3 existing tests + add new** (`tests/test_transpile.py`)

Update:

```python
# in test_transpile_function_simple_assignment:
    assert "let y = _py.add(x, 2);" in js   # was "let y = (x + 2);"

# in test_transpile_function_floor_div_and_mod:
    assert "Math.floor(s / 60)" in js
    assert "_py.mod(s, 60)" in js           # was "(s % 60)"

# in test_transpile_function_builtin_casts:
    assert "Math.trunc(Number(x))" in js
    assert "Number(x)" in js
    assert "_py.str(x)" in js               # was "String(x)"
    assert "_py.truthy(x)" in js
```

Append:

```python
def test_transpile_mul_uses_py():
    async def fn(s, items):
        a = s * 3
        b = items * 2

    js = transpile_function(fn)
    assert "_py.mul(s, 3)" in js
    assert "_py.mul(items, 2)" in js


def test_transpile_add_uses_py():
    async def fn(a, b):
        x = a + b

    js = transpile_function(fn)
    assert "_py.add(a, b)" in js


def test_transpile_len_uses_py():
    async def fn(d):
        x = len(d)

    js = transpile_function(fn)
    assert "_py.len(d)" in js


def test_transpile_str_uses_py():
    async def fn(items):
        x = str(items)

    js = transpile_function(fn)
    assert "_py.str(items)" in js
```

- [ ] **Step 2: Run — expect failures**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_transpile.py -v`
Expected: 3 updated + 4 new fail.

- [ ] **Step 3: Implement** in `violetear/transpile.py`.

In `_emit_expr`, `ast.BinOp` branch — after the `FloorDiv`/`Pow` special-cases and before `op = _BIN_OPS.get(type(node.op))`, insert:

```python
        if isinstance(node.op, ast.Add):
            return f"_py.add({l}, {r})"
        if isinstance(node.op, ast.Mult):
            return f"_py.mul({l}, {r})"
        if isinstance(node.op, ast.Mod):
            return f"_py.mod({l}, {r})"
```

In `_try_builtin`, replace the `len` and `str` cases:

```python
        case "len":
            return f"_py.len({pos_args[0]})"
```

```python
        case "str":
            return f"_py.str({pos_args[0]})" if pos_args else '""'
```

- [ ] **Step 4: Run — expect pass**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_transpile.py -v`
Expected: all pass.

- [ ] **Step 5: Node-verify a transpiled snippet computes correctly**

```bash
cd /home/apiad/Workspace/repos/violetear
cat > /home/apiad/Workspace/.playground/violetear-validators/seq_mod.py <<'PYX'
async def seq(items, name):
    line = name * 2
    return f"{line} has {len(items)} items, first repeats {str(items)}"
PYX
uv run python - <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("seq_mod","/home/apiad/Workspace/.playground/violetear-validators/seq_mod.py")
m = importlib.util.module_from_spec(spec); sys.modules["seq_mod"]=m; spec.loader.exec_module(m)
from violetear.transpile import transpile_function
open('/home/apiad/Workspace/.playground/violetear-validators/seq.js','w').write(transpile_function(m.seq))
PY
node --input-type=module -e "
import { readFileSync } from 'node:fs';
import assert from 'node:assert';
const rt = readFileSync('violetear/runtime.js','utf8');
const block = rt.slice(rt.indexOf('const _py = {'), rt.indexOf('// ReactiveRegistry'));
const fn = readFileSync('/home/apiad/Workspace/.playground/violetear-validators/seq.js','utf8');
const seq = new Function(block + '\n' + fn + '\nreturn seq;')();
assert.equal(await seq([1,2], 'ab'), \"abab has 2 items, first repeats [1, 2]\");
console.log('ok - transpiled seq computes Python semantics (mul, len, str)');
"
```
Expected: `ok - transpiled seq computes Python semantics (mul, len, str)`.

- [ ] **Step 6: Format + commit**

```bash
cd /home/apiad/Workspace/repos/violetear
uv run ruff format violetear/transpile.py tests/test_transpile.py
git add violetear/transpile.py tests/test_transpile.py
git commit -m "feat(transpile): Python %, *, +, len(), str() via _py helper"
```

---

### Task 3: Regression + roadmap

- [ ] **Step 1:** `cd /home/apiad/Workspace/repos/violetear && make` → exit 0. If any other test asserted an old `%`/`*`/`+`/`len`/`String` form, update it.
- [ ] **Step 2:** In `roadmap.md`, flip Phase 7 Slice 2 to `[x]` with the covered ops, and add a note that augmented assignment (`+=`/`*=`/`%=`) on collections is a deferred follow-up.
- [ ] **Step 3:** Commit `docs(roadmap): issue #9 slice 2 — numeric/sequence soundness`.

## Self-Review

- **Coverage:** `%`/`*`/`+` → Task 2 BinOp; `len`/`str` → Task 2 builtins; helpers → Task 1. Aug-assign explicitly deferred (documented). `bool()`-on-collections already in slice 1.
- **Placeholders:** none — full `_py` methods and every transpiler edit shown.
- **Type consistency:** `_py.mod/mul/add/len/str/repr` names match Task 1 (def) and Task 2 (emit). `Sub`/`Div` stay in `_BIN_OPS` (JS-correct for numbers). `FloorDiv`/`Pow` special-cases untouched.
