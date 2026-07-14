---
number: 8
title: "Safe, self-verifying JS codegen — signature-as-schema, cross-checked on both sides"
state: open
labels:
---

# Safe, self-verifying JS codegen

## 1. Problem

Violetear owns both sides of the wire: the server is Python, and the client is
*transpiled from* Python by `transpile.py`. Every boundary between them already
has exactly one contract written down — a Python type signature:

- `@app.server.rpc  async def report_count(current_count: int, action: str)`
- `@app.client.realtime async def update_alert(message: str, color: str)`
- `@app.local @dataclass class UiState: count: int = 0`

Today those annotations are **parsed and then discarded**. The generated JS
carries no contract, and no value crossing the wire is checked:

- `runtime.js` `socket.onmessage` (≈L237–245) does `JSON.parse(event.data)` then
  `scope[data.func](data.kwargs)` — a server-pushed payload flows straight into a
  typed `@app.client.realtime` handler with **zero validation**. A backend rename
  or a malformed frame silently passes `undefined` into the handler.
- The server-side inbound realtime dispatch in `app.py` `websocket_endpoint`
  (≈L411–452) calls `func(*args, **kwargs)` on client-supplied `kwargs` with **no
  validation** — a security-relevant trust boundary that trusts the client.
- The RPC client stub in `_generate_bundle_js` (≈L559–575) does
  `return r.json()` — the response is unchecked (`js.py:FetchResponse.json -> Any`).
- `transpile_class` (transpile.py:139–143) emits `set field(v) { ... }` — a bare,
  untyped setter; assigning the wrong type to reactive state is silent.

The one place already doing it right: `_register_rpc_route` (app.py:474–514)
builds a Pydantic model from the RPC signature via `create_model`, so FastAPI
validates the **inbound** client→server RPC body. That is the pattern to
generalize — to both directions of every boundary, and to the client side.

Non-negotiable constraints (from the framework's identity and the requesting
decision):

- **No JS build tooling.** No `tsc`, no `esbuild`, no `node` in the pipeline.
  The client validator must be plain JS we generate and serve from memory,
  exactly like `runtime.js` is today. (This rules out emitting TypeScript.)
- **Own the toolkit, or write our own.** We may vendor a third-party JS
  validator (e.g. Zod) only if we can ship it fully offline as a served asset.
  Default decision: **write our own tiny checker** — zero dependency, and we
  own the error messages.

## 2. Core principle: the signature *is* the schema, emitted on both sides

From each Python signature, generate a validator and enforce it at **both** ends
of the wire. The contract has one source of truth, so the two sides cannot drift
independently; if a value fails, it fails *at the seam* with a structured error
naming the field — never as `undefined` three calls deep.

Two validator backends, one source:

- **Server side → Pydantic.** Reuse the existing `create_model` pattern from
  `_register_rpc_route`. Pydantic is already a `[server]` dependency; no new code
  path. Build the model once per registered function from its signature.
- **Client side → our own generated `_check` JS.** From the same signature, emit
  calls into a small primitive library added to `runtime.js`. Zero dependency,
  no build step, structured errors we control.

Both are derived from the identical Python signature, so they *are* the
cross-check.

## 3. The boundaries and their emission sites

| Boundary | Contract source | Outgoing check (sender) | Incoming check (receiver) |
|---|---|---|---|
| **server→client realtime** (`@app.client.realtime` via `.invoke`/`.broadcast`) | the client handler's signature | **server**, Pydantic, in `SocketManager.broadcast`/`invoke` (app.py:265/282) before `json.dumps` | **client**, generated `_check`, in `runtime.js` dispatch before calling the handler |
| **client→server realtime** (`@app.server.realtime`) | the server handler's signature | **client**, generated `_check`, in the realtime send stub (`_generate_bundle_js` ≈L577–590) | **server**, Pydantic, in `websocket_endpoint` inbound dispatch (app.py:411–452) — *currently unchecked* |
| **client→server RPC** (`@app.server.rpc`) | the server function's signature + return annotation | **client**, generated `_check` on args, in the RPC send stub (≈L559–575) | **server** inbound already covered by `_register_rpc_route`; **client** validates the **response** `r.json()` against the return annotation |
| **reactive state** (`@app.local @dataclass`) | the dataclass field types | — | **client**, inline `_check` in the generated setter (transpile.py:139–143) |

The design realizes "cross-checks on both sides" literally: every wire boundary
validates on send *and* on receive, from the same signature. The server-side
check is the security-critical one (never trust the client); the client-side
check is the early-catch / DX one (fail before the network, with a clear error).

## 4. The client `_check` primitive library (added to `runtime.js`)

A small, dependency-free set of throwing validators. Each throws a
`VioletearValidationError` carrying a field `path` and the expected/actual
description. Structured like `ClientCompileError` in tone.

- `_checkBool(v, path)`, `_checkInt(v, path)`, `_checkNumber(v, path)`,
  `_checkStr(v, path)`
- `_checkList(v, path, elem)` — `elem` is a check fn applied per element
- `_checkDict(v, path, val)` — string keys, `val` check per value
- `_checkOptional(v, path, inner)` — allows `null`/`undefined`, else `inner`
- `_checkShape(v, path, fields)` — object with a `{name: checkFn}` map (nested
  dataclasses)
- `_validateKwargs(fnName, kwargs, spec)` — top-level entry: runs each field's
  check, aggregates, throws a single error listing all failures

`_checkInt` enforces integer-ness (`Number.isInteger`), since JS collapses
`int`/`float` to one numeric type — this is one place the generated check is
*stricter* than the raw JS would be, and that is the point.

## 5. Generated validator specs live in a bundle registry

`_generate_bundle_js` gains a section that emits, from the registered functions
and state classes, a `_VALIDATORS` registry mapping function name → a spec object
of `{field: checkExpr}`. Example:

```js
const _VALIDATORS = {
  update_alert: { message: _checkStr, color: _checkStr },
  report_count: { current_count: _checkInt, action: _checkStr },
};
```

- The **runtime dispatch** (`socket.onmessage`) calls
  `_validateKwargs(data.func, data.kwargs, _VALIDATORS[data.func])` before
  invoking the handler.
- The **send stubs** (RPC + realtime) call `_validateKwargs` on their args before
  `fetch`/`socket.send`.
- Reactive **setters** get an inline single-field check emitted directly by
  `transpile_class` (they are per-field, so no registry indirection needed).

Keeping the checks in a central registry (rather than inlined into every
generated function body) keeps the transpiled function output clean and puts the
whole contract surface in one inspectable place.

## 6. Supported type subset (v1)

Mirror the subset `_register_rpc_route`'s `create_model` already accepts, mapped
to `_check` primitives:

| Python annotation | Client check |
|---|---|
| `int` | `_checkInt` |
| `float` | `_checkNumber` |
| `str` | `_checkStr` |
| `bool` | `_checkBool` |
| `list[T]` | `_checkList(..., <T check>)` |
| `dict[str, V]` | `_checkDict(..., <V check>)` |
| `X \| None`, `Optional[X]` | `_checkOptional(..., <X check>)` |
| nested `@dataclass` | `_checkShape(..., {<fields>})` |
| missing / `Any` | no check (pass-through, documented) |

Unsupported annotations degrade to pass-through with **no silent surprise**:
emit a `console.warn`-free but source-commented `/* unchecked: <type> */` marker
and, at *generation* time, no error (so adopting the feature never breaks an
existing app). Nested unions beyond `X | None` and generics with type parameters
are out of scope for v1 — same boundary the RPC model already draws.

## 7. Error behavior

- Default: **strict** — a failed check throws `VioletearValidationError`. Fail
  loud, at the boundary.
- Server side surfaces the error the way `websocket_endpoint` already surfaces
  realtime handler errors (log + raise); a rejected inbound payload never reaches
  the handler.
- Client side: the thrown error propagates to the existing `.catch(...)` in the
  dispatch (`runtime.js` already wraps handler calls), logged with the field path.
- A future `App(validate="strict"|"warn"|"off")` switch is noted but **not** in
  v1 scope; v1 ships strict.

## 8. First vertical slice

**server→client realtime, validated on both sides.** The thinnest end-to-end
path that exercises the generator, the runtime primitives, *and* the both-sided
cross-check:

1. Add the `_check` primitives + `_validateKwargs` to `runtime.js`.
2. In `_generate_bundle_js`, emit the `_VALIDATORS` registry for
   `@app.client.realtime` functions from their signatures.
3. In the `runtime.js` `socket.onmessage` dispatch, validate `data.kwargs`
   against `_VALIDATORS[data.func]` before invoking.
4. In `SocketManager.broadcast`/`invoke`, build a Pydantic model from the target
   handler's signature and validate `kwargs` before `json.dumps`.

### Success criteria

- `update_alert.invoke(cid, message="hi", color=123)` raises a structured
  `pydantic.ValidationError`-derived error **on the server before the frame is
  sent** (unit-testable via `SocketManager`).
- A hand-crafted malformed inbound frame
  (`{"type":"rpc","func":"update_alert","kwargs":{"message":"hi","color":123}}`)
  is rejected by `_validateKwargs` in the client runtime with a
  `VioletearValidationError` naming `update_alert.color` — verified by a Node-free
  JS unit (evaluate `runtime.js` in a minimal JS harness) **or** a Playwright e2e
  in the existing `test_examples_e2e.py` style.
- A valid payload (`message="hi", color="green"`) passes both sides unchanged —
  no behavioral regression in `examples/05_realtime.py`.
- Adding the feature to an app that declares no type hints is a no-op (fields
  degrade to pass-through).

### Failure criteria (must NOT happen)

- No `node`/`tsc`/`esbuild` introduced anywhere.
- No new runtime Python dependency beyond the existing `[server]` extras.
- No behavioral change to apps whose handlers are fully valid.

## 9. Testing strategy

- **Server side:** unit tests in `tests/test_websocket.py` — `SocketManager`
  rejects mistyped `kwargs`, accepts valid ones; the generated Pydantic model
  matches the handler signature.
- **Client validator generation:** unit tests in `tests/test_transpile.py` /
  a new `tests/test_validators.py` — assert the emitted `_VALIDATORS` JS for a
  known signature (string equality on generated source, matching the existing
  bundle-emit test style).
- **Client runtime behavior:** the repo notes (issue 7.6/7.8) that pure-JS
  runtime paths have no server-side test and bite only in the browser. Add a
  minimal JS-eval harness that loads `runtime.js` and exercises `_validateKwargs`
  directly, so the runtime path is not left at 0% — this is the "Pyodide
  simulator" gap the AGENTS.md calls out, scoped to validators.
- **E2E:** extend `examples/05_realtime.py` coverage in `test_examples_e2e.py`
  to assert a malformed broadcast is rejected client-side.

## 10. Out of scope (tracked separately)

- **Semantic soundness of the transpiler** — the deeper "does the generated JS
  compute what the Python says" problem: `if my_list:` on `[]` (JS `[]` is
  truthy), `==`→`===` on lists/dicts (transpile.py:530/535), string `*`, `in`.
  These are silent *wrong-result* bugs, a different workstream from boundary
  validation. To be filed as **issue 9 (semantic soundness)**. Related in spirit
  to issue 7.6/7.7 (bundle drops module-level symbols) — the shared theme is
  "generated code correctness," but each is its own track.
- **TypeScript emission** — dropped by decision (requires a JS build step).

## 11. Reconciliation with existing issues

- **Issue 5 (unified server/client API):** this validation layer targets the
  *currently implemented* surface (`@app.server.rpc/realtime`,
  `@app.client.realtime`, `@app.local`) and does **not** depend on issue 5's
  refactor. It directly answers issue 5 §2.2's noted gap that "client-side DOM
  event handlers lack validation," generalized to the whole wire. If issue 5's
  renaming lands later, the validation hooks move with the decorators; the
  signature-as-schema principle is unchanged.
- **Issue 7 (framework gaps):** 7.6/7.7 (bundle drops module-level
  constants/imports) are a *missing-symbol* soundness gap, orthogonal to boundary
  validation but in the same "generated-code-correctness" family; they belong
  with the issue-9 semantic-soundness track, not here.

## 12. Open decisions (resolve during planning)

- Exact shape of the `_VALIDATORS` registry entry for nested dataclasses
  (inline `_checkShape` literal vs. a named sub-validator) — decide when the
  first nested case is implemented; v1 slice uses flat primitives only.
- Whether reactive-setter checks ship in the v1 slice or the immediate
  follow-up — leaning follow-up, to keep slice 1 to the realtime boundary.
