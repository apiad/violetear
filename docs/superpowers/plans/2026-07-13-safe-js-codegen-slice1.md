# Safe JS Codegen — Slice 1 (server→client realtime, both-sided) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make server→client realtime payloads self-verifying on both ends — the server validates outgoing kwargs (Pydantic) and the client validates the inbound frame (our own zero-dep JS checker) — both derived from the single `@app.client.realtime` Python signature.

**Architecture:** One new Python module (`violetear/validate.py`) derives, from a function signature, both a Pydantic model (server side) and a JS check-spec string (client side). The client checker primitives live in `runtime.js`. `ClientRegistry.realtime` caches both artifacts at decoration time; `SocketManager.broadcast`/`invoke` validate before sending; `_generate_bundle_js` emits a `_VALIDATORS` registry threaded into `Violetear_hydrate`, and the `runtime.js` WebSocket dispatch validates before invoking the handler.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic v2 (existing `[server]` extra), pytest + `fastapi.testclient.TestClient`, Playwright (existing e2e). No `node`/`tsc`/`esbuild`.

## Global Constraints

- Python **3.12+**; modern syntax (`list[str]`, `match`, `X | None`).
- **No JS build tooling** — no `tsc`/`esbuild`/`node`. Client validators are plain JS emitted and served from memory like `runtime.js`.
- **No new runtime Python dependency** beyond the existing `[server]` extras (FastAPI + Pydantic already present). Test-only deps are fine.
- Client validator = **our own code** (not Zod).
- **No behavioral change** for apps whose realtime payloads are valid; unsupported/absent annotations degrade to pass-through with no error.
- Formatting via `ruff format` (CI-enforced). Run `make format` before pushing.
- Slice-1 boundary: **server→client realtime only.** Client→server realtime, RPC arg/response checks, and reactive-setter checks are explicitly out of this plan.
- Commit conventional messages; work on `main`.

---

### Task 1: Signature → (Pydantic model + JS check-spec) derivation

**Files:**
- Create: `violetear/validate.py`
- Test: `tests/test_validate.py`

**Interfaces:**
- Consumes: nothing (foundation task).
- Produces:
  - `signature_to_model(func: Callable, model_name: str) -> type[pydantic.BaseModel]` — builds a Pydantic model from a function's typed params (skips `self`/`client_id`; missing annotation → `Any`; no default → required).
  - `js_check_spec(func: Callable) -> str` — returns a JS object-literal string mapping each param name to a `_check*` expression, e.g. `"{ message: _checkStr, color: _checkStr }"`. Empty params → `"{  }"`.
  - Supported annotation subset: `int`→`_checkInt`, `float`→`_checkNumber`, `str`→`_checkStr`, `bool`→`_checkBool`, `list[T]`→`(v, p) => _checkList(v, p, <T>)`, `dict[str, V]`→`(v, p) => _checkDict(v, p, <V>)`, `X | None`→`(v, p) => _checkOptional(v, p, <X>)`, nested `@dataclass`→`(v, p) => _checkShape(v, p, {<fields>})`, anything else / `Any` → `_checkAny`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validate.py
import dataclasses
import pytest
from violetear.validate import signature_to_model, js_check_spec


def _fn(message: str, color: str): ...
def _nums(count: int, ratio: float, flag: bool): ...
def _containers(tags: list[str], scores: dict[str, int]): ...
def _optional(note: str | None): ...
def _untyped(whatever): ...
def _skips(client_id: str, msg: str): ...


def test_js_check_spec_primitives():
    assert js_check_spec(_fn) == "{ message: _checkStr, color: _checkStr }"


def test_js_check_spec_numeric_and_bool():
    assert js_check_spec(_nums) == "{ count: _checkInt, ratio: _checkNumber, flag: _checkBool }"


def test_js_check_spec_containers():
    assert js_check_spec(_containers) == (
        "{ tags: (v, p) => _checkList(v, p, _checkStr), "
        "scores: (v, p) => _checkDict(v, p, _checkInt) }"
    )


def test_js_check_spec_optional():
    assert js_check_spec(_optional) == "{ note: (v, p) => _checkOptional(v, p, _checkStr) }"


def test_js_check_spec_untyped_is_passthrough():
    assert js_check_spec(_untyped) == "{ whatever: _checkAny }"


def test_js_check_spec_skips_client_id():
    assert js_check_spec(_skips) == "{ msg: _checkStr }"


def test_signature_to_model_validates_and_rejects():
    Model = signature_to_model(_fn, "FnKwargs")
    assert Model(message="hi", color="green").model_dump() == {"message": "hi", "color": "green"}
    with pytest.raises(Exception):
        Model(message="hi", color=123)


def test_signature_to_model_empty_params_ok():
    def _noargs(): ...
    Model = signature_to_model(_noargs, "NoArgsKwargs")
    assert Model().model_dump() == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_validate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'violetear.validate'`

- [ ] **Step 3: Write minimal implementation**

```python
# violetear/validate.py
"""Derive validators from a function signature — one source, both sides.

signature_to_model → a Pydantic model for server-side validation (reuses the
same create_model path App._register_rpc_route already uses for RPC bodies).
js_check_spec → a JS object-literal string of _check* expressions for the
client-side validator emitted into the bundle. Both read the identical
signature, so the two sides cannot drift.
"""

from __future__ import annotations

import dataclasses
import inspect
import types
from typing import Any, Callable, Union, get_args, get_origin

from pydantic import BaseModel, create_model

_SKIP_PARAMS = {"self", "client_id"}

_PRIMITIVE_CHECKS: dict[type, str] = {
    int: "_checkInt",
    float: "_checkNumber",
    str: "_checkStr",
    bool: "_checkBool",
}


def signature_to_model(func: Callable, model_name: str) -> type[BaseModel]:
    """Build a Pydantic model from a function's typed parameters."""
    sig = inspect.signature(inspect.unwrap(func))
    fields: dict[str, tuple] = {}
    for name, param in sig.parameters.items():
        if name in _SKIP_PARAMS:
            continue
        annotation = param.annotation
        if annotation is inspect.Parameter.empty:
            annotation = Any
        default = param.default
        if default is inspect.Parameter.empty:
            default = ...
        fields[name] = (annotation, default)
    return create_model(model_name, **fields)


def _js_checker(annotation: Any) -> str:
    """Return a JS check expression for one annotation (pass-through if unsupported)."""
    if annotation in _PRIMITIVE_CHECKS:
        return _PRIMITIVE_CHECKS[annotation]

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Union or origin is types.UnionType:
        non_none = [a for a in args if a is not type(None)]
        if len(args) == 2 and len(non_none) == 1:
            return f"(v, p) => _checkOptional(v, p, {_js_checker(non_none[0])})"
        return "_checkAny"

    if origin is list:
        elem = _js_checker(args[0]) if args else "_checkAny"
        return f"(v, p) => _checkList(v, p, {elem})"

    if origin is dict:
        val = _js_checker(args[1]) if len(args) == 2 else "_checkAny"
        return f"(v, p) => _checkDict(v, p, {val})"

    if dataclasses.is_dataclass(annotation):
        parts = [f"{f.name}: {_js_checker(f.type)}" for f in dataclasses.fields(annotation)]
        return f"(v, p) => _checkShape(v, p, {{{', '.join(parts)}}})"

    return "_checkAny"


def js_check_spec(func: Callable) -> str:
    """Return a JS object literal `{ name: <checker>, ... }` for a signature."""
    sig = inspect.signature(inspect.unwrap(func))
    entries: list[str] = []
    for name, param in sig.parameters.items():
        if name in _SKIP_PARAMS:
            continue
        annotation = param.annotation
        if annotation is inspect.Parameter.empty:
            annotation = Any
        entries.append(f"{name}: {_js_checker(annotation)}")
    return "{ " + ", ".join(entries) + " }"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_validate.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Format + commit**

```bash
cd /home/apiad/Workspace/repos/violetear
make format
git add violetear/validate.py tests/test_validate.py
git commit -m "feat(validate): signature -> pydantic model + JS check-spec derivation"
```

---

### Task 2: Client `_check` primitive library in `runtime.js`

**Files:**
- Modify: `violetear/runtime.js` (insert primitives after the `"use strict";` line, before `ReactiveRegistry`)
- Test: `tests/test_validators_e2e.py`

**Interfaces:**
- Consumes: nothing.
- Produces (globals in `runtime.js`): `VioletearValidationError`, `_checkAny`, `_checkStr`, `_checkBool`, `_checkNumber`, `_checkInt`, `_checkList`, `_checkDict`, `_checkOptional`, `_checkShape`, `_validateKwargs(fnName, kwargs, spec)`. Each `_check*` has shape `(v, path) => v` on success or throws `VioletearValidationError`. `_validateKwargs` aggregates per-field failures and throws one error whose `.message` contains `"<fnName>.<field>"`, or returns `kwargs` on success (no-op if `spec` is falsy).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validators_e2e.py
"""Exercise the runtime.js validator primitives in a real JS engine (Chromium)
via Playwright add_script_tag — no server, no Pyodide. Marked e2e because it
needs a browser. This closes the 'pure-JS runtime path is untested' gap
(AGENTS.md) for the validator library."""

from pathlib import Path

import pytest

RUNTIME_JS = (Path(__file__).resolve().parent.parent / "violetear" / "runtime.js").read_text()


def _load(page):
    page.set_content("<html><body></body></html>")
    page.add_script_tag(content=RUNTIME_JS)


@pytest.mark.e2e
def test_validate_kwargs_accepts_valid(page):
    _load(page)
    ok = page.evaluate(
        "() => { _validateKwargs('update_alert', {message:'hi', color:'green'}, "
        "{message:_checkStr, color:_checkStr}); return true; }"
    )
    assert ok is True


@pytest.mark.e2e
def test_validate_kwargs_rejects_wrong_type_naming_field(page):
    _load(page)
    err = page.evaluate(
        "() => { try { _validateKwargs('update_alert', {message:'hi', color:123}, "
        "{message:_checkStr, color:_checkStr}); return null; } "
        "catch (e) { return e.message; } }"
    )
    assert err is not None
    assert "update_alert.color" in err


@pytest.mark.e2e
def test_check_int_rejects_float(page):
    _load(page)
    err = page.evaluate(
        "() => { try { _checkInt(1.5, 'x.n'); return null; } catch (e) { return e.message; } }"
    )
    assert err is not None and "x.n" in err


@pytest.mark.e2e
def test_check_list_and_optional(page):
    _load(page)
    # list[str] with a bad element throws naming the index
    err = page.evaluate(
        "() => { try { _checkList(['a', 2], 'x.tags', _checkStr); return null; } "
        "catch (e) { return e.message; } }"
    )
    assert err is not None and "x.tags[1]" in err
    # optional accepts null
    ok = page.evaluate("() => { _checkOptional(null, 'x.note', _checkStr); return true; }")
    assert ok is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_validators_e2e.py -m e2e -v`
Expected: FAIL — `_validateKwargs is not defined` (ReferenceError surfaced by `page.evaluate`)

- [ ] **Step 3: Write minimal implementation**

Insert immediately after line 4 (`"use strict";`) in `violetear/runtime.js`:

```javascript
// ---------------------------------------------------------------------------
// Validator primitives — generated _VALIDATORS specs call into these.
// Zero-dependency. Each _check* is (value, path) => value | throw.
// ---------------------------------------------------------------------------
class VioletearValidationError extends Error {
  constructor(path, expected, got) {
    super(`${path}: expected ${expected}, got ${JSON.stringify(got)} (${typeof got})`);
    this.name = "VioletearValidationError";
    this.path = path;
  }
}
const _checkAny = (v) => v;
const _checkStr = (v, p) => {
  if (typeof v !== "string") throw new VioletearValidationError(p, "string", v);
  return v;
};
const _checkBool = (v, p) => {
  if (typeof v !== "boolean") throw new VioletearValidationError(p, "boolean", v);
  return v;
};
const _checkNumber = (v, p) => {
  if (typeof v !== "number" || Number.isNaN(v)) throw new VioletearValidationError(p, "number", v);
  return v;
};
const _checkInt = (v, p) => {
  if (typeof v !== "number" || !Number.isInteger(v)) throw new VioletearValidationError(p, "integer", v);
  return v;
};
const _checkList = (v, p, elem) => {
  if (!Array.isArray(v)) throw new VioletearValidationError(p, "list", v);
  v.forEach((x, i) => elem(x, `${p}[${i}]`));
  return v;
};
const _checkDict = (v, p, val) => {
  if (v === null || typeof v !== "object" || Array.isArray(v)) throw new VioletearValidationError(p, "object", v);
  for (const k of Object.keys(v)) val(v[k], `${p}.${k}`);
  return v;
};
const _checkOptional = (v, p, inner) => {
  if (v === null || v === undefined) return v;
  return inner(v, p);
};
const _checkShape = (v, p, fields) => {
  if (v === null || typeof v !== "object" || Array.isArray(v)) throw new VioletearValidationError(p, "object", v);
  for (const k of Object.keys(fields)) fields[k](v[k], `${p}.${k}`);
  return v;
};
function _validateKwargs(fnName, kwargs, spec) {
  if (!spec) return kwargs;
  const errors = [];
  for (const field of Object.keys(spec)) {
    try {
      spec[field](kwargs ? kwargs[field] : undefined, `${fnName}.${field}`);
    } catch (e) {
      errors.push(e.message);
    }
  }
  if (errors.length) {
    const e = new VioletearValidationError(fnName, "valid kwargs", kwargs);
    e.message = `${fnName}: ${errors.join("; ")}`;
    e.errors = errors;
    throw e;
  }
  return kwargs;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_validators_e2e.py -m e2e -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
cd /home/apiad/Workspace/repos/violetear
git add violetear/runtime.js tests/test_validators_e2e.py
git commit -m "feat(runtime): zero-dep _check validator primitives + _validateKwargs"
```

---

### Task 3: Server-side outgoing validation in `SocketManager`

**Files:**
- Modify: `violetear/app.py` — `ClientRegistry.__init__` (add caches), `ClientRegistry.realtime` (populate caches), `SocketManager.broadcast` and `SocketManager.invoke` (validate before `json.dumps`)
- Test: `tests/test_websocket.py` (append two tests)

**Interfaces:**
- Consumes: `signature_to_model` from Task 1; `ClientRealtimeStub` (existing).
- Produces:
  - `ClientRegistry._realtime_validators: dict[str, type[BaseModel]]` — name → Pydantic model.
  - `ClientRegistry._realtime_check_specs: dict[str, str]` — name → JS check-spec string (used by Task 4).
  - Behavior: `SocketManager.broadcast`/`invoke` raise `pydantic.ValidationError` when `kwargs` violate the target handler's signature, **before** any frame is sent.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_websocket.py
import pytest
from pydantic import ValidationError


def test_broadcast_rejects_mistyped_kwargs_before_send():
    """A server-side broadcast with kwargs that violate the @app.client.realtime
    signature raises before any frame reaches the wire."""
    app = App(title="WS-Validate-Out", version="wsv1")

    @app.client.realtime
    async def notify(message: str, level: str):
        pass

    @app.view("/")
    def home():
        return Document(title="x")

    with pytest.raises(ValidationError):
        # level must be str; 123 is rejected by the generated Pydantic model
        import asyncio

        asyncio.run(notify.broadcast(message="hello", level=123))


def test_broadcast_accepts_valid_kwargs_and_sends_envelope():
    """Valid kwargs pass validation and produce the unchanged envelope shape."""
    app = App(title="WS-Validate-Out-OK", version="wsv2")

    @app.client.realtime
    async def notify(message: str, level: str):
        pass

    @app.server.rpc
    async def kick() -> dict:
        await notify.broadcast(message="hi", level="info")
        return {"ok": True}

    @app.view("/")
    def home():
        return Document(title="x")

    client = TestClient(app.api)
    with client.websocket_connect("/_violetear/ws?client_id=v") as ws:
        r = client.post("/_violetear/rpc/kick", json={})
        assert r.status_code == 200
        msg = ws.receive_json()
    assert msg == {
        "type": "rpc",
        "func": "notify",
        "args": [],
        "kwargs": {"message": "hi", "level": "info"},
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_websocket.py -k validate -v`
Expected: FAIL — `test_broadcast_rejects_mistyped_kwargs_before_send` does not raise (no validation yet).

- [ ] **Step 3: Write minimal implementation**

In `violetear/app.py`, add the import near the top (after the existing `.transpile` import on line 18):

```python
from .validate import signature_to_model, js_check_spec
```

In `ClientRegistry.__init__` (currently ends at the `self._lifecycle` line ~179), add two caches:

```python
        self._realtime_validators: dict[str, type] = {}  # name -> pydantic model
        self._realtime_check_specs: dict[str, str] = {}  # name -> JS check-spec
```

In `ClientRegistry.realtime`, after `self._compiled_functions[func.__name__] = ("realtime", js)` (currently line ~231), populate the caches from the raw `func`:

```python
        self._realtime_validators[func.__name__] = signature_to_model(
            func, f"{func.__name__}Kwargs"
        )
        self._realtime_check_specs[func.__name__] = js_check_spec(func)
```

Add a private helper on `SocketManager` and call it at the top of `broadcast` and `invoke` (before the `payload = json.dumps(...)` line in each):

```python
    def _validate_outgoing(self, func_name: str, kwargs: dict):
        """Validate server->client realtime kwargs against the handler signature.

        Raises pydantic.ValidationError before the frame is serialized/sent.
        No model registered (e.g. untyped handler) -> no-op.
        """
        model = self.app.client._realtime_validators.get(func_name)
        if model is not None:
            model(**kwargs)
```

Then in `broadcast`, insert as the first line of the method body:

```python
        self._validate_outgoing(func_name, kwargs)
```

And identically as the first line of `invoke`'s body:

```python
        self._validate_outgoing(func_name, kwargs)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_websocket.py -v`
Expected: PASS (all existing WS tests + the 2 new ones). The existing `test_reverse_rpc_broadcast_envelope_shape` still passes (its kwargs are valid strings).

- [ ] **Step 5: Format + commit**

```bash
cd /home/apiad/Workspace/repos/violetear
make format
git add violetear/app.py tests/test_websocket.py
git commit -m "feat(app): validate outgoing realtime kwargs server-side before send"
```

---

### Task 4: Emit `_VALIDATORS` into the bundle + validate on inbound client dispatch

**Files:**
- Modify: `violetear/app.py` — `_generate_bundle_js` (emit `_VALIDATORS`, thread it into the hydrate call)
- Modify: `violetear/runtime.js` — `Violetear_hydrate` (read `opts.validators`), `_setup_websocket` (accept validators, validate inbound before dispatch)
- Test: `tests/test_engine.py` (bundle-emit string assertion) + extend `tests/test_examples_e2e.py`

**Interfaces:**
- Consumes: `ClientRegistry._realtime_check_specs` (Task 3), `_validateKwargs` + `_check*` (Task 2).
- Produces:
  - Bundle contains `const _VALIDATORS = { <name>: <spec>, ... };` for every realtime handler, and the final call becomes `Violetear_hydrate(_scope, { storage_prefix: "...", validators: _VALIDATORS });`.
  - `runtime.js` `socket.onmessage` validates `data.kwargs` against `validators[data.func]` before invoking; on failure it `console.error`s the field path and drops the frame (does not call the handler).

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_engine.py
from violetear import App, Document


def test_bundle_emits_validators_registry_for_realtime():
    app = App(title="Bundle-Validators", version="bv1")

    @app.client.realtime
    async def update_alert(message: str, color: str):
        pass

    @app.view("/")
    def home():
        return Document(title="x")

    bundle = app._generate_bundle_js()
    assert "const _VALIDATORS = {" in bundle
    assert "update_alert: { message: _checkStr, color: _checkStr }" in bundle
    # threaded into hydrate opts
    assert "validators: _VALIDATORS" in bundle


def test_bundle_validators_empty_when_no_realtime():
    app = App(title="Bundle-NoRealtime", version="bv2")

    @app.client.callback
    async def click(event):
        pass

    @app.view("/")
    def home():
        return Document(title="x")

    bundle = app._generate_bundle_js()
    # registry still emitted (empty) and threaded, so runtime never sees undefined
    assert "const _VALIDATORS = {" in bundle
    assert "validators: _VALIDATORS" in bundle
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_engine.py -k validators -v`
Expected: FAIL — `"const _VALIDATORS = {"` not found in bundle.

- [ ] **Step 3: Write minimal implementation**

In `violetear/app.py` `_generate_bundle_js`, after the realtime-stub loop (section "# 4. JS realtime stubs", ends ~line 590) and before section "# 5. Scope object", insert:

```python
        # 4.5 Validator registry for @app.client.realtime handlers.
        # Threaded into Violetear_hydrate so the WS dispatch can check inbound
        # kwargs before invoking the handler. Always emitted (possibly empty)
        # so runtime.js never references an undefined binding.
        validator_entries: list[str] = []
        for fn_name, (kind, _js) in self.client._compiled_functions.items():
            if kind == "realtime":
                spec = self.client._realtime_check_specs.get(fn_name, "{  }")
                validator_entries.append(f"  {fn_name}: {spec}")
        validators_block = ",\n".join(validator_entries)
        parts.append(f"const _VALIDATORS = {{\n{validators_block}\n}};")
```

Then change the final hydrate call (currently the last `parts.append(...)` in the method) to thread the registry through opts:

```python
        parts.append(
            f"const _scope = {{\n"
            f"  _lifecycle: {{\n{lifecycle_block}\n  }},\n"
            f"{scope_block}\n"
            f"}};\n"
            f'Violetear_hydrate(_scope, {{ storage_prefix: "{storage_prefix}", validators: _VALIDATORS }});'
        )
```

In `violetear/runtime.js`, update `_setup_websocket` to accept and use `validators`, and validate inbound before dispatch. Replace the current `_setup_websocket(scope)` signature and its `socket.onmessage` handler:

```javascript
function _setup_websocket(scope, validators) {
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
      if (!fn) { console.warn(`[violetear] rpc handler not found: ${data.func}`); return; }
      try {
        _validateKwargs(data.func, data.kwargs ?? {}, validators?.[data.func]);
      } catch (e) {
        console.error(`[violetear] invalid inbound payload for ${data.func}:`, e.message);
        return;
      }
      fn(data.kwargs ?? {}).catch(e => console.error(`[violetear] rpc error in ${data.func}:`, e));
    }
  };

  socket.onclose = () => {
    const handlers = scope._lifecycle?.disconnect ?? [];
    handlers.forEach(fn => fn().catch(() => {}));
    setTimeout(() => _setup_websocket(scope, validators), 3000);
  };
}
```

Update `Violetear_hydrate` to read validators from opts and pass them through. Replace the `needs_websocket` block near the end of `Violetear_hydrate`:

```javascript
  const validators = opts.validators ?? {};
  const needs_websocket = Object.keys(scope).some(k => !k.startsWith("_"));
  if (needs_websocket) _setup_websocket(scope, validators);
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_engine.py -v`
Expected: PASS (existing engine tests + the 2 new ones).

- [ ] **Step 5: Add the end-to-end reject test**

```python
# append to tests/test_examples_e2e.py

@pytest.mark.e2e
def test_05_realtime_rejects_malformed_inbound_frame(example_server, page):
    """A server-pushed frame whose kwargs violate the @app.client.realtime
    signature is rejected in the client runtime (console.error naming the
    field) and never reaches the handler — proving the inbound cross-check."""
    base = example_server("05_realtime.py")

    seen_errors: list[str] = []
    page.on(
        "console",
        lambda msg: seen_errors.append(msg.text) if msg.type == "error" else None,
    )

    page.goto(base + "/")
    page.wait_for_function(
        "() => document.getElementById('violetear-cloak') === null",
        timeout=HYDRATION_TIMEOUT_MS,
    )

    # Directly drive the runtime's dispatch with a malformed frame for a real
    # realtime handler. In examples/05_realtime.py, `receive_message(msg: dict)`
    # expects `msg` to be a dict; sending an int must be rejected by the
    # generated _VALIDATORS entry (`_checkDict`), naming `receive_message.msg`.
    rejected = page.evaluate(
        """() => {
          try {
            _validateKwargs('receive_message', { msg: 123 }, _VALIDATORS['receive_message']);
            return null;
          } catch (e) { return e.message; }
        }"""
    )
    assert rejected is not None
    assert "receive_message.msg" in rejected
```

Note: adjust `func`/`kwargs` to a real `@app.client.realtime` handler in `examples/05_realtime.py` and one of its typed params (read the example first). If `_VALIDATORS` is not reachable from `page.evaluate` (it is a bundle-module `const`), attach it in the bundle via the hydrate opts is already done; if the const is not in the evaluate scope, fall back to asserting on the `console.error` path by triggering a real malformed broadcast from the server test instead.

- [ ] **Step 6: Run the e2e**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_examples_e2e.py -k malformed -m e2e -v`
Expected: PASS (the malformed frame is rejected with a message naming the handler).

- [ ] **Step 7: Format + commit**

```bash
cd /home/apiad/Workspace/repos/violetear
make format
git add violetear/app.py violetear/runtime.js tests/test_engine.py tests/test_examples_e2e.py
git commit -m "feat(codegen): emit _VALIDATORS registry + validate inbound realtime frames client-side"
```

---

### Task 5: Full-suite regression + example smoke

**Files:**
- No new source. Verifies no regression across the whole suite and the canonical realtime example.

**Interfaces:**
- Consumes: everything from Tasks 1–4.
- Produces: a green full suite, proving valid payloads are unaffected (the "no behavioral change" failure-criterion from the spec).

- [ ] **Step 1: Run the fast unit gate**

Run: `cd /home/apiad/Workspace/repos/violetear && make`
Expected: PASS — ruff format-check clean, all non-e2e tests pass.

- [ ] **Step 2: Run the e2e suite**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest -m e2e -v`
Expected: PASS — including `test_05_realtime_chat_message_round_trips_to_dom` (valid payloads still round-trip unchanged) and the new reject test.

- [ ] **Step 3: Update the roadmap + issue status**

Add to `roadmap.md` under a new "Phase 6 — Safe codegen" section:

```markdown
## Phase 6 — Safe, self-verifying codegen

- [x] Slice 1: server→client realtime validated on both sides (issue #8)
- [ ] Slice 2: client→server realtime + RPC arg/response validation
- [ ] Slice 3: reactive-setter field validation
```

- [ ] **Step 4: Commit**

```bash
cd /home/apiad/Workspace/repos/violetear
git add roadmap.md
git commit -m "docs(roadmap): Phase 6 slice 1 — both-sided realtime validation shipped"
```

---

## Self-Review

**Spec coverage:**
- §2 signature-as-schema, two backends → Task 1 (`signature_to_model` + `js_check_spec`).
- §3 server→client realtime, both sides → Task 3 (server outgoing) + Task 4 (client inbound). Other boundaries explicitly deferred (slice boundary).
- §4 `_check` primitive library → Task 2.
- §5 `_VALIDATORS` registry threaded through hydrate → Task 4.
- §6 supported subset → Task 1 `_js_checker` + Task 1 tests.
- §7 strict-throw error behavior → Task 2 (`_validateKwargs` throws), Task 3 (Pydantic raises), Task 4 (inbound rejects + logs).
- §8 first-slice success/failure criteria → Tasks 3, 4, 5.
- §9 testing strategy → Task 1 (generation), Task 3 (server), Task 2 (client library e2e), Task 4/5 (e2e).
- §10 out of scope → not implemented (correct); roadmap notes future slices.

**Placeholder scan:** No TBD/TODO in source steps. The one conditional note (Task 4 Step 5) gives an explicit fallback and instructs reading `examples/05_realtime.py` for the real handler/param names — the executor must ground the frame in the actual example rather than a guessed name.

**Type consistency:** `signature_to_model(func, model_name)` and `js_check_spec(func)` names match across Tasks 1/3/4. `_realtime_validators`/`_realtime_check_specs` cache names match between Task 3 (populate) and Tasks 3/4 (read). `_validateKwargs(fnName, kwargs, spec)` and the `_check*` `(v, path)` shape match between Task 2 (def) and Task 4 (call). Wire `type` string is `"rpc"` for server→client throughout (matches `SocketManager` and existing `test_reverse_rpc_broadcast_envelope_shape`).
