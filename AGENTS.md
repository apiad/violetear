# AGENTS.md — violetear

This file is the door for any AI coding agent working in this repo. Read it
first. Other tools (Codex, OpenCode, Cursor, Aider) auto-load it; for Claude
Code it's loaded via the workspace convention in `~/Workspace/CLAUDE.md`.

There is also an `AGENT.md` (singular) — Alex's personal protocol describing
how to *think* before coding (Understand → Plan → Develop → Document). That
file is voice/process; **this file (AGENTS.md, plural) is structural**.

## What violetear is

A full-stack isomorphic Python web framework. FastAPI + uvicorn on the
server; a Python→JS AST compiler + vanilla-JS runtime on the client (no
Pyodide, no WASM). Ships a server-side HTML builder (`markup.Element`,
`HTML.div(...)`), a two-tier reactive state layer:

- `@app.local` — per-tab reactive dataclass compiled to a JS singleton; field
  assignments inside `@app.client.*` update the DOM automatically.
- `@app.shared` — cross-client reactive dataclass; field assignments on the
  server or from any client automatically broadcast a `shared_sync` WebSocket
  frame to all connections — zero boilerplate collaborative state.

Also ships: a Python→JS compiler (`transpile.py`), a vanilla-JS runtime
(`runtime.js`: ~500 lines, ReactiveRegistry, `_shared` dispatcher, DOM,
storage, WebSocket, hydration), browser API stubs (`js.py`), a WebSocket RPC
bus (`@app.server.rpc` / `@app.client.realtime`), a CSS DSL (`Style`,
`StyleSheet`), and PWA scaffolding. No JS framework, no templates, no htmx.

Vault node: `vault/Efforts/Repos/violetear.md` (in Alex's workspace).

## Layout

```
violetear/          package source
  app.py            App, ClientRegistry, ServerRegistry, SocketManager, bundle gen
  shared.py         SharedProxy, SharedRegistry, SharedStateError (@app.shared)
  markup.py         Element, Document, HTML builder, Component
  state.py          @local decorator, ReactiveProxy, LeafProxy
  transpile.py      Python→JS AST compiler: ClientCompileError, transpile_class(shared=), transpile_function
  js.py             Browser API stubs for IDE/mypy: DOM, localStorage, sessionStorage, sleep, fetch, …
  runtime.js        Vanilla-JS runtime: ReactiveRegistry, _shared dispatcher, _ws_send, hydration (~500 lines)
  style.py          fluent style builder
  stylesheet.py     stylesheet builder, selectors
  color.py          Color class + Colors named-color registry
  pwa.py            Manifest, ServiceWorker generators
  presets.py        FlexGrid, SemanticDesign, UtilitySystem, Atomic
tests/              pytest suite
  test_shared.py    SharedProxy, SharedRegistry, App.shared, handle_set, bundle emission
docs/               quarto docs site + example .py files (consumed by test_examples.py)
examples/           canonical demos, one per tier (01_static → 06_shared)
issues/             design docs for unimplemented features
.github/workflows/  CI (ruff format-check + pytest on push/PR)
roadmap.md          phased roadmap (Phases 1-8)
AGENT.md            Alex's code-agent thinking protocol (orthogonal to this file)
```

## Conventions

- **Python 3.12+** required. Use modern features: `match`, `list[str]` (not
  `typing.List[str]`), generic `[T]` syntax on functions/classes.
- **Type hints** on public APIs; loose typing inside private methods OK.
- **Async** for any function that crosses the server/client boundary
  (`@app.server.rpc`, `@app.server.realtime`, `@app.client.callback`,
  `@app.client.realtime`, lifecycle handlers). Sync handlers are rejected
  at decoration time with `ValueError`.
- **Decorator order** matters for `@app.local` and `@app.shared`: the app
  decorator goes *outside* `@dataclass`. For `@app.shared`, the class name
  in user code becomes the `SharedProxy` singleton — identical to how
  `@app.local` works for JS singletons.
- **`@app.shared` field metadata**: `field(metadata={"server_only": True})`
  marks a field as server-writable only. The client receives `shared_sync`
  updates for it but its `_shared.set()` call is stripped from the emitted
  setter, and the server rejects any `shared_set` frames for it with
  `shared_error`. Enforcement is runtime-only in v1; compiler enforcement
  is filed as issue #11.
- **Module-level defs** for any class/function passed to `@app.local` or
  `@app.client.*`. The bundle generator dedents source so nested defs
  work in tests, but real apps should define these at module scope for
  predictability and IDE support.
- **Formatting** via `ruff format`. CI enforces it. Run `make format`
  before pushing or let `make` (default = `test-unit`) fail loudly.
- **No JS framework**. No htmx. If you find yourself reaching for one,
  build the missing primitive in Python instead.

## Common workflows

### Run the test suite

```bash
make                # = make test-unit (ruff format-check + pytest --cov)
make test-all       # also collects tests outside tests/ (rarely needed)
```

CI runs the same gate on every push/PR (`.github/workflows/tests.yml`).

### Add a feature

1. Read the relevant `issues/<n>-...md` design doc if one exists; otherwise
   draft one before coding non-trivial surface.
2. Update `roadmap.md` checkboxes when shipping a phase item.
3. Pin behavior with a test in the matching file (`tests/test_<surface>.py`).
   Coverage gates aren't enforced but new compiler/runtime paths should
   have unit tests in `tests/test_transpile.py` or `tests/test_js_shims.py`.

### Fix a bug found in production usage

If the bug shows up in an example (e.g. `examples/*.py`), the example is
documentation; fix it too. If the bug is in the framework, add a
regression test pinning the new behavior before flipping the production
code — characterization first prevents accidental re-regression.

### Release

```bash
NEW_VERSION=1.4.0 make release
```

This:
1. Verifies formatting + runs the full suite.
2. Bumps `pyproject.toml` and `violetear/__init__.py` (they must stay in sync).
3. Commits, tags `v1.4.0`, pushes commit + tag, creates a GitHub release.

Never bump versions manually — the makefile is the single source of truth
so the two version files don't drift.

## Surfaces with limited test coverage

Be extra careful when touching these — regressions are easy because the
test suite won't catch them:

- **`runtime.js`** — vanilla-JS runtime, no JS test harness. Bundle-generation
  tests pin *what gets emitted* but not the in-browser behavior. E2E tests
  (Playwright, manual) are the only gate.
- **Style/StyleSheet fluent methods** (`.padding`, `.font`, `.border`,
  `.flex`, …) — black-box tested against fixtures in `tests/test_examples.py`
  via expected `.css` outputs in `tests/expected_outputs/`, no unit tests.
- **`Component` subclasses + `ElementSet.spawn`** — pattern exists in
  `markup.py` but no examples or tests exercise it.

## Things to NOT do

- Don't broadcast from `@app.server.on("startup")`. At startup there are
  zero active websocket connections; clients reconnect after startup. Use
  `@app.server.on("connect")` + `.invoke(client_id, ...)` to greet new
  clients, or `.broadcast(...)` from inside a request handler when there
  are already-connected clients.
- Don't mutate `@app.shared` fields in-place (e.g. `Room.users[k] = v`
  or `Room.messages.append(x)`). In-place mutation bypasses `SharedProxy.
  __setattr__` so the change is never broadcast. Always reassign:
  `Room.users = {**Room.users, k: v}` or
  `Room.messages = Room.messages + [x]`.
- Don't import `violetear.dom`, `violetear.storage`, or `violetear.client`
  — these modules were deleted in v2.0. Use `from violetear.js import DOM,
  localStorage, sessionStorage` inside `@app.client.*` functions instead.
- Don't put PII or secrets in `examples/`. They're shipped in PyPI sdists.
- Don't add a new third-party runtime dependency without first checking
  whether the workspace already has a sibling lib (in `repos/`) that
  provides the capability. Cross-repo reuse: `vault/Atlas/Architecture/`
  may have a relevant design doc.

## Know-how index

*(Empty for now. Add procedure docs to `know-how/<topic>.md` as recurring
tasks emerge — testing a new client-side feature, debugging a Pyodide
bundle failure, profiling render performance, etc. Each entry here gets a
short "when to reach for it" line so future agents can match by intent.)*
