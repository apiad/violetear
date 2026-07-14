# Safe JS Codegen — Slice 3 (reactive-setter field validation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** `@app.local @dataclass` reactive-state setters validate the assigned value against the field type before mutating + notifying — so `UiState.count = "x"` throws at the boundary instead of silently corrupting state.

**Architecture:** Reuse the `_check*` primitives and `validate._js_checker`. `transpile_class` resolves field types via `typing.get_type_hints` (handles `from __future__ import annotations`) and emits a check call at the top of each generated setter.

**Tech Stack:** Python 3.12+, pytest, node (local JS verification). No JS build tooling.

## Global Constraints

- Same as Slices 1–2: no JS build tooling; our own checker; unsupported/absent annotations → pass-through (`_checkAny`); `uv run ruff format` (not `make format`); work on `main`.
- Strict-throw on violation (consistent with slices 1–2).
- No regression: existing `transpile_class` tests stay green (they assert `notify(...)` presence, not full setter text).

---

### Task 1: Public `js_type_check` wrapper

**Files:** Modify `violetear/validate.py`; Test `tests/test_validate.py`.

**Interfaces:** Produces `js_type_check(annotation) -> str` — a JS check expression for a *resolved* type (thin public wrapper over `_js_checker`; `None`/unknown → `_checkAny`).

- [ ] **Step 1: Failing test** (append to `tests/test_validate.py`)

```python
from violetear.validate import js_type_check


def test_js_type_check_primitives_and_containers():
    assert js_type_check(int) == "_checkInt"
    assert js_type_check(str) == "_checkStr"
    assert js_type_check(list) == "(v, p) => _checkList(v, p, _checkAny)"
    assert js_type_check(None) == "_checkAny"
```

- [ ] **Step 2: Run — expect ImportError**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_validate.py -k type_check -v`

- [ ] **Step 3: Implement** (append to `violetear/validate.py`)

```python
def js_type_check(annotation: Any) -> str:
    """Public: JS check expression for an already-resolved type annotation."""
    if annotation is None:
        return "_checkAny"
    return _js_checker(annotation)
```

- [ ] **Step 4: Run — expect pass**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_validate.py -v`

- [ ] **Step 5: Format + commit**

```bash
cd /home/apiad/Workspace/repos/violetear
uv run ruff format violetear/validate.py tests/test_validate.py
git add violetear/validate.py tests/test_validate.py
git commit -m "feat(validate): public js_type_check wrapper for resolved annotations"
```

---

### Task 2: Setter validation in `transpile_class`

**Files:** Modify `violetear/transpile.py`; Test `tests/test_transpile.py`.

**Interfaces:** Consumes `js_type_check`. Produces setters of the form
`set count(v) { (_checkInt)(v, "UiState.count"); this._count = v; ReactiveRegistry.notify("UiState.count", v); }`.
Field types resolved via `typing.get_type_hints(cls)` (falls back to `_checkAny` if resolution fails or the field is unannotated).

- [ ] **Step 1: Failing test** (append to `tests/test_transpile.py`)

```python
def test_transpile_class_setter_validates_field_type():
    @dataclass
    class UiState:
        count: int = 0
        label: str = "x"

    js = transpile_class(UiState)
    assert '(_checkInt)(v, "UiState.count");' in js
    assert '(_checkStr)(v, "UiState.label");' in js
    # still mutates + notifies after the check
    assert 'ReactiveRegistry.notify("UiState.count", v);' in js
```

- [ ] **Step 2: Run — expect fail**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_transpile.py -k setter_validates -v`

- [ ] **Step 3: Implement** in `violetear/transpile.py`.

Add `import typing` near the top imports (after `import textwrap`), and `from .validate import js_type_check` at module top (no cycle: validate.py does not import transpile).

In `transpile_class`, replace the getter/setter emission loop:

```python
    try:
        hints = typing.get_type_hints(cls)
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
```

- [ ] **Step 4: Run — expect pass, plus full transpile file green**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_transpile.py -v`

- [ ] **Step 5: Node-verify a generated setter rejects a wrong-typed assignment**

```bash
cd /home/apiad/Workspace/repos/violetear
uv run python - <<'PY'
from dataclasses import dataclass
from violetear.transpile import transpile_class
@dataclass
class UiState:
    count: int = 0
open('/home/apiad/Workspace/.playground/violetear-validators/state.js','w').write(transpile_class(UiState))
print('wrote')
PY
node --input-type=module -e "
import { readFileSync } from 'node:fs';
const rt = readFileSync('violetear/runtime.js','utf8');
const block = rt.slice(rt.indexOf('class VioletearValidationError'), rt.indexOf('// ReactiveRegistry'));
const cls = readFileSync('/home/apiad/Workspace/.playground/violetear-validators/state.js','utf8');
globalThis.ReactiveRegistry = { notify(){} };
const UiState = new Function(block + '\n' + cls + '\nreturn UiState;')();
UiState.count = 5;  // ok
let msg=null; try { UiState.count = 'nope'; } catch(e){ msg=e.message; }
if (!msg || !msg.includes('UiState.count')) throw new Error('expected setter validation error, got: '+msg);
console.log('ok - setter rejected wrong type:', JSON.stringify(msg), '| valid assign kept:', UiState.count);
"
```
Expected: prints `ok - setter rejected wrong type: ... | valid assign kept: 5`.

- [ ] **Step 6: Format + commit**

```bash
cd /home/apiad/Workspace/repos/violetear
uv run ruff format violetear/transpile.py tests/test_transpile.py
git add violetear/transpile.py tests/test_transpile.py
git commit -m "feat(transpile): validate reactive-state assignments in generated setters"
```

---

### Task 3: Regression + roadmap

- [ ] **Step 1:** `cd /home/apiad/Workspace/repos/violetear && make` → exit 0.
- [ ] **Step 2:** In `roadmap.md`, flip Slice 3 to `[x]`.
- [ ] **Step 3:** Commit `docs(roadmap): Phase 6 slice 3 — reactive-setter validation shipped`.

## Self-Review

- Coverage: spec §3 reactive-state row → Task 2; supporting public API → Task 1.
- Placeholders: none. Node harness is complete and self-contained.
- Consistency: `js_type_check` name matches across tasks; setter check form `(<checker>)(v, "Class.field")` parenthesizes both bare (`_checkInt`) and arrow checkers so both are callable.
