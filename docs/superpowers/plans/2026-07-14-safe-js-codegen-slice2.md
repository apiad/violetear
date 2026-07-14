# Safe JS Codegen — Slice 2 (client→server realtime + RPC, + RPC response) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Extend both-sided validation to the client→server directions — RPC and realtime — plus validate the RPC *response* on the client, all from the same Python signatures.

**Architecture:** Reuse Slice 1's `validate.py` derivation and `runtime.js` `_check*` primitives. Add a return-type checker; extend the emitted `_VALIDATORS` registry to cover `@app.server.rpc` and `@app.server.realtime` (so the client send stubs validate outgoing args) and add a `_RETURN_VALIDATORS` registry (so RPC stubs validate the response). Server-side, validate inbound `@app.server.realtime` kwargs in `websocket_endpoint` (currently unchecked; RPC inbound is already validated by FastAPI via `_register_rpc_route`).

**Tech Stack:** Python 3.12+, FastAPI, Pydantic v2, pytest + TestClient, node (local verification of generated JS). No `node`/`tsc`/`esbuild` in the pipeline.

## Global Constraints

- Same as Slice 1: Python 3.12+; **no JS build tooling**; no new runtime dep beyond `[server]`; our own JS checker; unsupported/absent annotations degrade to pass-through; format via `uv run ruff format` (not `make format`); work on `main`; conventional commits.
- Slice-2 boundary: **client→server realtime, client→server RPC (args + response).** Reactive-setter checks (Slice 3) and semantic soundness (issue #9) remain out.
- No regression: existing WS/RPC tests (incl. `test_realtime_message_dispatches_to_server_function`, which sends **positional** args) must stay green.

---

### Task 1: Return-type checker (`js_return_check`)

**Files:**
- Modify: `violetear/validate.py`
- Test: `tests/test_validate.py`

**Interfaces:**
- Consumes: `_js_checker` (Slice 1).
- Produces: `js_return_check(func) -> str` — a single JS check expression for the function's return annotation (`eval_str` resolved). No annotation / `None` / `Any` → `_checkAny`.

- [ ] **Step 1: Write the failing test** (append to `tests/test_validate.py`)

```python
from violetear.validate import js_return_check


def _ret_dict(x: int) -> dict: ...
def _ret_none(x: int) -> None: ...
def _ret_untyped(x: int): ...
def _ret_str(x: int) -> str: ...


def test_js_return_check_dict():
    assert js_return_check(_ret_dict) == "(v, p) => _checkDict(v, p, _checkAny)"


def test_js_return_check_str():
    assert js_return_check(_ret_str) == "_checkStr"


def test_js_return_check_none_is_any():
    assert js_return_check(_ret_none) == "_checkAny"


def test_js_return_check_untyped_is_any():
    assert js_return_check(_ret_untyped) == "_checkAny"
```

- [ ] **Step 2: Run — expect fail**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_validate.py -k return -v`
Expected: FAIL — `ImportError: cannot import name 'js_return_check'`

- [ ] **Step 3: Implement** (append to `violetear/validate.py`)

```python
def js_return_check(func: Callable) -> str:
    """Return a single JS check expression for a function's return annotation."""
    sig = inspect.signature(inspect.unwrap(func), eval_str=True)
    ann = sig.return_annotation
    if ann is inspect.Signature.empty or ann is type(None):
        return "_checkAny"
    return _js_checker(ann)
```

- [ ] **Step 4: Run — expect pass**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_validate.py -v`
Expected: PASS (14 total)

- [ ] **Step 5: Format + commit**

```bash
cd /home/apiad/Workspace/repos/violetear
uv run ruff format violetear/validate.py tests/test_validate.py
git add violetear/validate.py tests/test_validate.py
git commit -m "feat(validate): js_return_check for RPC response validation"
```

---

### Task 2: Server-side inbound realtime validation

**Files:**
- Modify: `violetear/app.py` — `ServerRegistry.__init__` (cache), `ServerRegistry.realtime` (populate + a `_validate_incoming` helper), `websocket_endpoint` inbound realtime block (validate-and-skip)
- Test: `tests/test_websocket.py`

**Interfaces:**
- Consumes: `signature_to_model` (Slice 1).
- Produces:
  - `ServerRegistry._realtime_validators: dict[str, type]` — name → Pydantic model.
  - `ServerRegistry._validate_incoming(func_name, args, kwargs)` — binds positional args to param names (excluding `client_id`), merges with kwargs, validates against the model; raises `pydantic.ValidationError` on mismatch; no-op if no model.
  - Behavior: a malformed inbound `@app.server.realtime` frame is logged and **skipped** (handler not called, connection stays open).

- [ ] **Step 1: Write the failing test** (append to `tests/test_websocket.py`)

```python
def test_inbound_realtime_rejects_mistyped_kwargs_and_skips_handler():
    """A client→server realtime frame with a wrong-typed field is rejected
    server-side: the handler is not called and the connection stays open."""
    app = App(title="WS-Inbound-Validate", version="wsv3")

    seen = []

    @app.client.realtime
    async def ack():
        pass

    @app.server.realtime
    async def record(action: str, count: int):
        seen.append((action, count))
        await ack.broadcast()

    @app.view("/")
    def home():
        return Document(title="x")

    client = TestClient(app.api)
    with client.websocket_connect("/_violetear/ws?client_id=z") as ws:
        # count must be int; "oops" is rejected → handler skipped, no ack sent.
        ws.send_json(
            {"type": "realtime", "func": "record", "args": [], "kwargs": {"action": "x", "count": "oops"}}
        )
        # A valid follow-up proves the connection survived and dispatch still works.
        ws.send_json(
            {"type": "realtime", "func": "record", "args": [], "kwargs": {"action": "ok", "count": 3}}
        )
        ack_msg = ws.receive_json()

    assert ack_msg["func"] == "ack"
    assert seen == [("ok", 3)]  # the mistyped call never ran


def test_inbound_realtime_positional_args_still_validate_and_run():
    """The existing positional-args path (args=[...], kwargs={}) still binds and
    validates — regression guard for test_realtime_message_dispatches."""
    app = App(title="WS-Inbound-Pos", version="wsv4")

    seen = []

    @app.client.realtime
    async def ack():
        pass

    @app.server.realtime
    async def record(action: str, count: int):
        seen.append((action, count))
        await ack.broadcast()

    @app.view("/")
    def home():
        return Document(title="x")

    client = TestClient(app.api)
    with client.websocket_connect("/_violetear/ws?client_id=p") as ws:
        ws.send_json({"type": "realtime", "func": "record", "args": ["click", 7], "kwargs": {}})
        ack_msg = ws.receive_json()

    assert ack_msg["func"] == "ack"
    assert seen == [("click", 7)]
```

- [ ] **Step 2: Run — expect first test to fail**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_websocket.py -k inbound -v`
Expected: `test_inbound_realtime_rejects_mistyped_kwargs_and_skips_handler` FAILS (handler runs on bad input; `seen` has 2 entries / ack fires for the bad one). The positional test passes today.

- [ ] **Step 3: Implement**

In `ServerRegistry.__init__` (after `self.event_handlers` line), add:

```python
        self._realtime_validators: dict[str, type] = {}  # name -> pydantic model
```

In `ServerRegistry.realtime`, after `self.realtime_functions[func.__name__] = wrapper` (and before `return wrapper`), add:

```python
        self._realtime_validators[func.__name__] = signature_to_model(
            func, f"{func.__name__}InKwargs"
        )
```

Add a helper method to `ServerRegistry`:

```python
    def _validate_incoming(self, func_name: str, args: list, kwargs: dict):
        """Validate an inbound client→server realtime payload against the
        handler signature. Binds positional args to param names (skipping
        client_id) so both the kwargs and positional forms validate. Raises
        pydantic.ValidationError on mismatch; no-op if no model registered."""
        model = self._realtime_validators.get(func_name)
        if model is None:
            return
        func = self.realtime_functions[func_name]
        params = [
            p
            for p in inspect.signature(inspect.unwrap(func)).parameters
            if p != "client_id"
        ]
        merged = dict(kwargs)
        for name, val in zip(params, args):
            merged[name] = val
        model(**merged)
```

In `websocket_endpoint`, inside `if func_name in self.server.realtime_functions:` and right after `func = self.server.realtime_functions[func_name]` (line ~439), insert a validate-and-skip guard *before* the existing `try:`:

```python
                            try:
                                self.server._validate_incoming(func_name, args, kwargs)
                            except Exception as _ve:
                                print(
                                    f"[Violetear] ⚠️ Rejected invalid inbound realtime "
                                    f"'{func_name}': {_ve}"
                                )
                                continue
```

- [ ] **Step 4: Run — expect pass**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_websocket.py -v`
Expected: PASS (all existing + 2 new; `test_realtime_message_dispatches_to_server_function` still green).

- [ ] **Step 5: Format + commit**

```bash
cd /home/apiad/Workspace/repos/violetear
uv run ruff format violetear/app.py tests/test_websocket.py
git add violetear/app.py tests/test_websocket.py
git commit -m "feat(app): validate inbound client->server realtime kwargs (skip on reject)"
```

---

### Task 3: Client send-stub validation (RPC args + response, realtime args)

**Files:**
- Modify: `violetear/app.py` — `_generate_bundle_js` (extend `_VALIDATORS` to rpc+realtime; emit `_RETURN_VALIDATORS`; rewrite RPC + realtime send stubs to validate)
- Test: `tests/test_engine.py` (bundle string assertions)

**Interfaces:**
- Consumes: `js_check_spec`, `js_return_check` (Task 1); `_validateKwargs`, `_check*` (Slice 1 runtime).
- Produces: bundle in which
  - `_VALIDATORS` also contains entries for every `@app.server.rpc` and `@app.server.realtime` function;
  - `_RETURN_VALIDATORS = { <rpcName>: <returnChecker>, ... }` is emitted and threaded is NOT needed (bundle-local `const`, referenced directly by the RPC stubs which live in the same bundle);
  - each RPC stub calls `_validateKwargs("<name>", {args}, _VALIDATORS["<name>"])` before `fetch` and applies `_RETURN_VALIDATORS["<name>"]` to the parsed response;
  - each realtime send stub calls `_validateKwargs("<name>", {args}, _VALIDATORS["<name>"])` before `socket.send`.

- [ ] **Step 1: Write the failing test** (append to `tests/test_engine.py`)

```python
def test_rpc_stub_validates_args_and_response():
    app = App(title="RPC-Validate", version="rv1")

    @app.server.rpc
    async def report_count(current_count: int, action: str) -> dict:
        return {"ok": True}

    @app.view("/")
    def home():
        return Document(title="x")

    bundle = app._generate_bundle_js()
    # args validated before fetch
    assert '_validateKwargs("report_count", { current_count, action }, _VALIDATORS["report_count"])' in bundle
    # response validated against the return annotation (dict)
    assert "const _RETURN_VALIDATORS = {" in bundle
    assert "report_count: (v, p) => _checkDict(v, p, _checkAny)" in bundle
    assert '_RETURN_VALIDATORS["report_count"]' in bundle
    # _VALIDATORS carries the rpc kwargs spec too
    assert "report_count: { current_count: _checkInt, action: _checkStr }" in bundle


def test_realtime_send_stub_validates_args():
    app = App(title="RT-Send-Validate", version="rv2")

    @app.server.realtime
    async def telemetry(x: int, y: int):
        pass

    @app.view("/")
    def home():
        return Document(title="x")

    bundle = app._generate_bundle_js()
    assert '_validateKwargs("telemetry", { x, y }, _VALIDATORS["telemetry"])' in bundle
    assert "telemetry: { x: _checkInt, y: _checkInt }" in bundle
```

- [ ] **Step 2: Run — expect fail**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_engine.py -k "rpc_stub_validates or realtime_send_stub" -v`
Expected: FAIL — the `_validateKwargs(...)`/`_RETURN_VALIDATORS` strings are absent.

- [ ] **Step 3: Implement** in `_generate_bundle_js`.

Replace the RPC stub loop (section "# 3. JS RPC stubs") body with a version that validates args + response:

```python
        # 3. JS RPC stubs for @app.server.rpc — validate args before fetch and
        #    the response after (both derived from the Python signature).
        for name, func in self.server.rpc_functions.items():
            sig = inspect.signature(func)
            params = [p.name for p in sig.parameters.values() if p.name != "client_id"]
            param_str = ", ".join(params)
            destructured = ", ".join(params)
            parts.append(
                f"async function {name}({{{destructured}}}) {{\n"
                f'  _validateKwargs("{name}", {{ {param_str} }}, _VALIDATORS["{name}"]);\n'
                f'  const r = await fetch("/_violetear/rpc/{name}", {{\n'
                f'    method: "POST",\n'
                f'    headers: {{"Content-Type": "application/json"}},\n'
                f"    body: JSON.stringify({{{param_str}}})\n"
                f"  }});\n"
                f"  if (!r.ok) throw new Error(`RPC error: ${{r.status}}`);\n"
                f"  const _data = await r.json();\n"
                f'  const _rc = _RETURN_VALIDATORS["{name}"];\n'
                f'  if (_rc) _rc(_data, "{name}(): return");\n'
                f"  return _data;\n"
                f"}}"
            )
```

Replace the realtime send-stub loop (section "# 4. JS realtime stubs") body:

```python
        # 4. JS realtime stubs for @app.server.realtime — validate args before send.
        for name, func in self.server.realtime_functions.items():
            sig = inspect.signature(func)
            params = [p.name for p in sig.parameters.values() if p.name != "client_id"]
            param_str = ", ".join(params)
            destructured = ", ".join(params)
            parts.append(
                f"async function {name}({{{destructured}}}) {{\n"
                f'  _validateKwargs("{name}", {{ {param_str} }}, _VALIDATORS["{name}"]);\n'
                f"  window.violetear_socket.send(JSON.stringify({{\n"
                f'    type: "realtime", func: "{name}",\n'
                f"    args: [], kwargs: {{{param_str}}}\n"
                f"  }}));\n"
                f"}}"
            )
```

Extend the `_VALIDATORS` emission (section "# 4.5") to also include server rpc + realtime specs, and emit `_RETURN_VALIDATORS`. Replace the section-4.5 block with:

```python
        # 4.5 Validator registries. _VALIDATORS: kwargs specs for every boundary
        # (client.realtime inbound + server.rpc/realtime outgoing). _RETURN_VALIDATORS:
        # response checkers for rpc. Always emitted (possibly empty) so the bundle
        # never references an undefined binding.
        validator_entries: list[str] = []
        for fn_name, (kind, _js) in self.client._compiled_functions.items():
            if kind == "realtime":
                spec = self.client._realtime_check_specs.get(fn_name, "{  }")
                validator_entries.append(f"  {fn_name}: {spec}")
        for name, func in self.server.rpc_functions.items():
            validator_entries.append(f"  {name}: {js_check_spec(func)}")
        for name, func in self.server.realtime_functions.items():
            validator_entries.append(f"  {name}: {js_check_spec(func)}")
        validators_block = ",\n".join(validator_entries)
        parts.append(f"const _VALIDATORS = {{\n{validators_block}\n}};")

        return_entries: list[str] = []
        for name, func in self.server.rpc_functions.items():
            return_entries.append(f"  {name}: {js_return_check(func)}")
        return_block = ",\n".join(return_entries)
        parts.append(f"const _RETURN_VALIDATORS = {{\n{return_block}\n}};")
```

Add `js_return_check` to the existing import at the top of `app.py`:

```python
from .validate import signature_to_model, js_check_spec, js_return_check
```

- [ ] **Step 4: Run — expect pass**

Run: `cd /home/apiad/Workspace/repos/violetear && uv run pytest tests/test_engine.py -v`
Expected: PASS (existing + 2 new). Note: the Slice-1 `test_bundle_emits_validators_registry_for_realtime` still passes (client.realtime entries unchanged).

- [ ] **Step 5: Node-verify a generated RPC stub rejects bad args before fetch**

```bash
cd /home/apiad/Workspace/repos/violetear
uv run python -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('rv','/dev/stdin')
" <<'PY'
PY
uv run python - <<'PY'
from violetear import App, Document
app = App(title='n', version='n')
@app.server.rpc
async def report_count(current_count: int, action: str) -> dict:
    return {'ok': True}
@app.view('/')
def home(): return Document(title='x')
b = app._generate_bundle_js()
open('/home/apiad/Workspace/.playground/violetear-validators/bundle_rpc.js','w').write(b)
print('wrote bundle')
PY
node --input-type=module -e "
import { readFileSync } from 'node:fs';
const rt = readFileSync('violetear/runtime.js','utf8');
const block = rt.slice(rt.indexOf('class VioletearValidationError'), rt.indexOf('// ReactiveRegistry'));
const bundle = readFileSync('/home/apiad/Workspace/.playground/violetear-validators/bundle_rpc.js','utf8');
// extract just the report_count function + registries from the bundle
const fn = bundle.slice(bundle.indexOf('async function report_count'), bundle.indexOf('const _scope'));
globalThis.fetch = () => { throw new Error('FETCH CALLED — validation did not stop bad args'); };
globalThis.window = {};
const run = new Function(block + '\n' + fn + '\nreturn report_count;')();
let msg=null; try { await run({ current_count: 'not-an-int', action: 'x' }); } catch(e){ msg=e.message; }
if (!msg || !msg.includes('report_count.current_count')) throw new Error('expected validation error, got: '+msg);
console.log('ok - RPC stub rejected bad args before fetch:', JSON.stringify(msg));
"
```
Expected: prints `ok - RPC stub rejected bad args before fetch: ...` (fetch never called).

- [ ] **Step 6: Format + commit**

```bash
cd /home/apiad/Workspace/repos/violetear
uv run ruff format violetear/app.py tests/test_engine.py
git add violetear/app.py tests/test_engine.py
git commit -m "feat(codegen): validate RPC args+response and realtime send args client-side"
```

---

### Task 4: Regression + roadmap

- [ ] **Step 1: Full unit gate**

Run: `cd /home/apiad/Workspace/repos/violetear && make`
Expected: exit 0, all unit tests pass, format clean.

- [ ] **Step 2: Update roadmap** — flip Slice 2 to done in `roadmap.md`:

```markdown
- [x] **Slice 2**: client→server realtime + RPC arg/response validation.
```

- [ ] **Step 3: Commit**

```bash
cd /home/apiad/Workspace/repos/violetear
git add roadmap.md
git commit -m "docs(roadmap): Phase 6 slice 2 — client->server + RPC validation shipped"
```

## Self-Review

- **Coverage:** spec §3 RPC row (client args + response; server inbound already via FastAPI) → Tasks 1+3; spec §3 client→server realtime row (client args; server inbound) → Tasks 2+3. `_VALIDATORS`/`_RETURN_VALIDATORS` → Task 3. Return checker → Task 1.
- **Placeholders:** none — all steps carry real code/commands. The Task-3 Step-5 node harness has a stray empty heredoc scaffold; the operative block is the second `uv run python - <<'PY'` + the `node --input-type=module` check.
- **Type consistency:** `js_return_check`, `_RETURN_VALIDATORS`, `ServerRegistry._realtime_validators`, `_validate_incoming(func_name, args, kwargs)` names consistent across tasks. `_validateKwargs(name, {args}, _VALIDATORS[name])` call shape matches Slice-1 runtime signature. Positional-args binding in `_validate_incoming` guards the existing positional test.
