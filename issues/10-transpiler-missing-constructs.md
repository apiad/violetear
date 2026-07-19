---
number: 10
title: "Transpiler missing constructs: comprehensions, tuple unpacking, computed format specs"
state: open
labels: transpiler
---

# Transpiler missing constructs

Gaps discovered during a systematic playground exercise (2026-07-18). Each raises
a clear `ClientCompileError` rather than silently emitting wrong code — the safe
failure mode. Filing here as a prioritised backlog.

---

## 10.1 — List comprehensions

**Symptom.** `[x * 2 for x in items]` raises `unsupported-construct: unsupported
expression: '[x * 2 for x in items]'`.

**Frequency.** High — list comprehensions are idiomatic Python and the first
thing users reach for when building transformed lists.

**Suggested translation.**

```python
[x * 2 for x in items]
# → (items).map((x) => _py.mul(x, 2))
```

Filter (`[x for x in items if x > 0]`) maps to `.filter(...).map(...)`.
Nested comprehensions can be deferred.

**Where to fix.** `_emit_expr` in `transpile.py` — add a branch for `ast.ListComp`.
Each comprehension `for x in iter if cond` maps to a chained `.filter().map()`.
The loop variable must be added to a fresh inner scope (not `ctx`) so it doesn't
pollute the outer `_declared` set.

---

## 10.2 — Tuple unpacking in assignment

**Symptom.** `a, b = pair` raises `unsupported-construct: unsupported assignment
target: '(a, b)'`.

**Frequency.** Medium — common when iterating `d.items()` outside a for loop,
or when a function returns a tuple.

**Suggested translation.**

```python
a, b = some_call()
# → let _t = some_call(); let a = _t[0]; let b = _t[1];
```

Simple fixed-width unpacking only (no starred `*rest`).

**Where to fix.** `_emit_assignment_target` — detect `ast.Tuple` target with all
`ast.Name` elements, evaluate RHS once into a temp, emit index reads.

---

## 10.3 — Computed f-string format specs

**Symptom.** `f"{n:{width}d}"` raises `unsupported-construct: computed f-string
format spec is not supported; use a constant like f'{x:02d}'`.

**Frequency.** Low — mostly affects layout/table rendering. Constant format specs
(`f"{n:03d}"`) already work via `_py.format`.

**Suggested translation.** The runtime already has `_py.format(value, spec)`.
A computed spec just needs to construct the spec string at runtime:

```python
f"{n:{width}d}"
# → `${_py.format(n, `${width}d`)}`
```

**Where to fix.** `_constant_format_spec` in `transpile.py` — when the format
spec is not a constant, emit a nested template literal instead of raising.

---

## 10.4 — Dict comprehensions

**Symptom.** `{k: v for k, v in pairs}` raises `unsupported-construct: unsupported
expression: '{k: val for k in keys}'`.

**Frequency.** Low — dict comprehensions are less common in UI code than list
comprehensions. `Object.fromEntries` is the natural JS target.

**Suggested translation.**

```python
{k: transform(v) for k, v in d.items()}
# → Object.fromEntries(Object.entries(d).map(([k, v]) => [k, transform(v)]))
```

Single-iterable `{k: expr for k in lst}` → `Object.fromEntries(lst.map(k => [k, expr]))`.

**Where to fix.** `_emit_expr` — add branch for `ast.DictComp`. Like list comps,
use a fresh inner scope for loop variables.

---

## Priority order

Recommended shipping order based on user impact:

1. **10.2 tuple unpacking** — small, high-value. Already used naturally after `d.items()`.
2. **10.1 list comprehensions** — idiomatic Python, most missed.
3. **10.3 computed format specs** — small isolated fix.
4. **10.4 dict comprehensions** — niche, defer until list comps land.
