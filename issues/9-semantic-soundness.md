---
number: 9
title: "Semantic soundness — generated JS must compute what the Python means"
state: open
labels:
---

# Semantic soundness of the Python→JS transpiler

## 1. Problem

Issue #8 made every *value crossing a boundary* validated. This issue is the
deeper one: the transpiler (`transpile.py`) is a "looks-right" subset that, for
several constructs, emits JS which **silently computes a different result** than
the Python would. Validation doesn't help — the value is "valid", it's just
*wrong*, because the operation was mistranslated.

Audit of the current output (verified via `_emit_expr`/`_emit_stmt`):

| Python | Emits today | Wrong because |
|---|---|---|
| `if items:` | `if (items)` | `[]`/`{}` are **falsy** in Python, **truthy** in JS |
| `items or 5` | `(items \|\| 5)` | `[] or 5` → Python `5`, JS `[]` (JS truthiness) |
| `not items` | `(!items)` | `not []` → Python `True`, JS `false` |
| `items == [1, 2]` | `(items === [1, 2])` | list/dict equality → Python by value, JS by reference (always false) |
| `n % 3` | `(n % 3)` | `-7 % 3` → Python `2`, JS `-1` |
| `s * 3` | `(s * 3)` | `"a" * 3` → Python `"aaa"`, JS `NaN` |
| `len(d)` | `d.length` | `len({})` → Python `0`, JS `undefined` |
| `f"{n:02d}"` | `` `${n}` `` | **format spec silently dropped** — live bug in `examples/04_pwa.py` |
| `n in items` | *compile error* | unsupported (fails loud — the safe kind, not a wrong result) |

Most are silent wrong-result bugs (dangerous). `in`/`not in` merely raise a
`ClientCompileError` today (safe, but a missing feature). One — the f-string
format-spec drop — already ships broken in example 04's `f"{minutes:02d}"`.

Constraints (unchanged from issue #8): **no JS build tooling**; **our own JS**;
degrade unsupported cases without silent wrongness.

## 2. Approach: a runtime `_py` semantics library

Same move that worked for validation. Add a small, zero-dependency `_py` object
to `runtime.js` whose methods replicate Python semantics, and have the transpiler
emit calls to them. Correct regardless of the runtime type, no build step, no
type system required.

Rejected alternatives: **type-directed translation** (client code isn't fully
typed, so it degrades to guessing exactly where semantics matter most);
**restrict-and-fail** (rejecting ordinary Python fights the "write real Python"
promise).

Cost accepted: generated JS is less readable (operations wrapped in `_py.*`) and
marginally slower. Correctness wins for generated code.

## 3. Decomposition (multi-slice)

- **Slice 1 (this spec): truthiness + equality + f-string format specs.** The
  most common, most silently-wrong cases; also fixes the live example-04 bug.
- **Slice 2: numeric/sequence** — `%` (floored), `*` (repeat), `+` (list concat),
  `len(dict)`, `str()`/`bool()` on collections.
- **Slice 3: membership** — `in` / `not in` (currently a compile error → real feature).

## 4. Slice 1 design

### 4.1 The `_py` runtime helper (added to `runtime.js`)

A single `const _py = { ... }`, sibling to the `_check*` primitives, loaded before
the bundle:

- **`_py.truthy(x)`** — Python truthiness:
  - `boolean` → itself; `null`/`undefined` → `false`
  - `number` → `x !== 0` (so `0`/`0.0` falsy; `NaN` truthy, matching Python)
  - `string` → `x.length > 0`
  - array → `x.length > 0`
  - other object → `Object.keys(x).length > 0` (dict/`{}` case; plain-object =
    dict assumption, documented)
  - fallback → `true`
- **`_py.and(a, bf)` / `_py.or(a, bf)`** — operand-returning, short-circuit;
  `bf` is a thunk so the right operand isn't evaluated (or double-evaluated):
  - `and(a, bf) => _py.truthy(a) ? bf() : a`
  - `or(a, bf) => _py.truthy(a) ? a : bf()`
- **`_py.eq(a, b)` / `_py.ne(a, b)`** — deep structural equality (recursive over
  arrays and plain objects); scalars fall back to `===`. `ne` is `!eq`.
  Known minor gap (documented): `True == 1` is `True` in Python but `_py.eq`
  returns `false` (bool≠number); rare in client code.
- **`_py.format(value, spec)`** — Python format-spec mini-language, common subset:
  `[fill][0][width][.precision][type]` for types `d`, `f`, `s`, `x` (+ default).
  Covers `02d` (zero-pad width), `.2f` (fixed precision), `s`, `x` (hex), plain.
  Unrecognized spec → `String(value)` (no silent numeric corruption).

### 4.2 Transpiler wiring (`transpile.py`)

- **`if` / `while` test, ternary test** → wrap in `_py.truthy(...)`. Wrapping a
  comparison result is a harmless no-op (`_py.truthy(true) === true`), so all
  conditions are wrapped uniformly for simplicity.
- **`not x`** (`ast.UnaryOp`/`ast.Not`) → `!_py.truthy(x)` (was `(!x)`).
- **`and` / `or`** (`ast.BoolOp`) → `_py.and(a, () => b)` / `_py.or(a, () => b)`,
  folded right for chains: `a and b and c` → `_py.and(a, () => _py.and(b, () => c))`.
- **`==` / `!=`** (`ast.Compare` `Eq`/`NotEq`) → `_py.eq(l, r)` / `_py.ne(l, r)`.
  (`is None` / `is not None` keep their existing `=== null` / `!== null` forms.)
- **`bool(x)`** builtin → `_py.truthy(x)` (was `Boolean(x)`).
- **f-string `FormattedValue` with a `format_spec`** → `_py.format(expr, "<spec>")`;
  no format_spec → existing `${expr}`. (The `format_spec` is itself a `JoinedStr`;
  for slice 1 support only *constant* format specs, e.g. `:02d`; a computed spec
  raises `ClientCompileError` — fail loud, not silent.)

### 4.3 Tests that change

Several existing `tests/test_transpile.py` cases assert exact JS strings for the
rewritten constructs and MUST be updated to the new `_py.*` forms (characterization
update, not a regression): the if/elif/else, while, ternary, and any `==`/`not`/
`and`/`or` cases. This is expected and part of the slice.

## 5. Success criteria

- `_py.truthy([])` is `false`, `_py.truthy([1])` is `true`, `_py.truthy(0)` false,
  `_py.truthy("")` false, `_py.truthy({})` false — verified in a JS engine (node).
- `_py.eq([1,2],[1,2])` is `true`; `_py.eq({a:1},{a:1})` is `true`;
  `_py.eq([1],[2])` is `false`.
- `_py.or([], () => 5)` returns `5`; `_py.and([1], () => 2)` returns `2`.
- `_py.format(5, "02d")` is `"05"`; `_py.format(3.14159, ".2f")` is `"3.14"`.
- A transpiled `if items:` emits `if (_py.truthy(items))`; `items == [1,2]` emits
  `_py.eq(items, [1, 2])`; `f"{n:02d}"` emits `_py.format(n, "02d")` — asserted in
  `tests/test_transpile.py`.
- **No regression**: full `make` gate green (existing transpile tests updated to the
  new forms); example apps still behave correctly (their conditions are scalar
  comparisons; the f-string fix makes example-04's time display correct).

## 6. Failure criteria (must NOT happen)

- No `node`/`tsc`/`esbuild` in the pipeline (`_py` is served JS, like `runtime.js`).
- No new runtime dependency.
- No construct silently changes to a *different wrong* result (unrecognized format
  specs and computed format specs fail loud or pass through as `String`, never
  silently corrupt).

## 7. Out of scope (this slice)

- Slice 2 (numeric/sequence) and Slice 3 (membership) per §3.
- Full CPython format-spec mini-language (grouping `,`, alignment `<>^`, sign
  options, `%`/`e`/`g` types) — slice-1 covers the common subset; the rest degrade
  to `String(value)`.
- `bool == int` equivalence edge case (§4.1).
