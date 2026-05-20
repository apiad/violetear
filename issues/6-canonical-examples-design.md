---
number: 6
title: "Canonical Examples — Design Spec"
state: open
labels:
---

# Canonical Examples for violetear

**Status:** Draft → review
**Date:** 2026-05-20

## Goal

Replace `examples/` (currently 9 ad-hoc files with overlapping concerns) with a minimal canonical set of **5 progressively-richer, independent showcases** that together stress-test the entire shipped violetear surface, while each remaining simple enough to read end to end.

Each example is independent — readable in isolation, no shared helper module, no assumption that the previous example has been read. The progression is in *capability tier*, not in domain or code reuse.

## Scope

**In scope:**
- Rewrite `examples/` from scratch — delete all 9 existing files, add 5 new ones.
- One thin smoke test per example in `tests/test_examples_canonical.py` so they don't bit-rot when the framework changes.
- File-naming convention: numeric prefix (`01_`, `02_`, …) so they sort by tier.

**Out of scope (deferred):**
- Deep pedagogical documentation (decided 2026-05-20: defer until after the set lands).
- `@app.shared` usage in tier 5 — feature is unimplemented (`issues/4-...md`). Tier 5 uses the manual `@app.server.realtime` + broadcast pattern that is the only currently-working multi-user shape. When `@app.shared` ships, example 5 gets revised.
- A `Component` subclass showcase — pattern exists in `markup.py:Component` but no example currently exercises it; deferred to a future addition.
- A dedicated CSS DSL deep dive — coverage in `docs/examples/` (the Quarto fixture set) is already adequate for the DSL itself.
- Any new framework features. Gaps found during the build get filed as a new `issues/` entry and continue; we do not stop the build to fix the framework unless a gap is blocking.

**Untouched:**
- `docs/examples/` and `tests/test_examples.py` (CSS fixture suite — separate purpose).
- `tests/test_engine.py`, `test_state.py`, `test_websocket.py`, `test_pwa.py`, `test_unit.py` (framework unit/integration tests — orthogonal to the new examples).

## The 5 tiers (overview)

| # | File | Tier | Domain | Surface stressed |
|---|---|---|---|---|
| 1 | `01_static.py` | Pure markup + CSS, no server | Design-tokens reference page | `Document`, `Element`, `HTML.*`, `StyleSheet`, `Style`, `Color`/`Colors`, units. Writes `01_static.html` + `01_static.css` to disk. |
| 2 | `02_ssr.py` | Server-only, no Pyodide bundle | Guestbook (GET list + POST add) | `App`, `@app.view`, served stylesheet via `doc.style(href=...)`, native FastAPI form handling, multiple routes. |
| 3 | `03_interactive.py` | SSR + client-side Python, single user | Unit converter (m / ft / in, with a server-side "precise" mode) | `@app.client.callback`, `@app.local` reactive state, `data-bind-text`/`-value`, `@app.client.on("ready")`, `@app.server.rpc`, `violetear.dom.DOM` API. |
| 4 | `04_pwa.py` | Installable + offline | Pomodoro timer | `pwa=Manifest(...)`, Service Worker asset caching, `violetear.storage` for cross-reload state, `@app.local` + persistent backing, an `asyncio` tick loop on the client. |
| 5 | `05_realtime.py` | Multi-user via WebSocket | Chat room with presence | `@app.server.on("connect")`/`("disconnect")`, `@app.server.realtime`, `@app.client.realtime` with `.broadcast()` and `.invoke(client_id, ...)`, manual server-side shared state (`messages: list`, `users: dict[client_id, name]`). |

## Detailed designs

### 01 — Design-tokens reference page (`01_static.py`)

**Domain.** A single-page design-tokens reference: palette swatches, typography scale (h1–h6 + body + small + caption), spacing scale (4 / 8 / 16 / 24 / 32 / 48 / 64 px), and a section showing all `Unit` types side by side.

**Shape.**
- No `App`, no FastAPI import.
- Build a `Document` + `StyleSheet` in module scope.
- `if __name__ == "__main__":` writes `01_static.html` and `01_static.css` to the same directory as the script.
- Top-of-file docstring: "Run `python examples/01_static.py` then open `01_static.html` in a browser."

**Concretely stresses.**
- `StyleSheet` with many `.select(...)` rules.
- `Style` fluent builder (`.font(...)`, `.color(...)`, `.padding(...)`, `.background(...)`, `.border(...)`, `.rounded(...)`, `.flexbox(...)`).
- A wide slice of `Colors.*` (named color registry).
- Multiple `Unit` types (px, rem, %, em).
- `Document` with `head` styles, `body` content tree, `HTML.div(...).style(...)` chaining, `ElementSet.spawn(...)` for the swatch grid.

**Verification.** Test imports the module, invokes its build function, asserts `<!DOCTYPE html>` in rendered HTML and a known color hex in rendered CSS.

### 02 — Guestbook (`02_ssr.py`)

**Domain.** A guestbook: GET `/` shows a list of entries (name + message + timestamp) plus a form; POST `/entries` appends an entry and redirects back to `/`.

**Shape.**
- Module-level `app = App(title="Guestbook")`.
- Module-level `entries: list[dict] = []` — in-memory store; reset on restart, intentional simplicity.
- `@app.view("/")` returns a `Document` rendering the list + the form.
- `@app.api.post("/entries")` accepts form fields (FastAPI's native form handling — we don't introduce a new violetear primitive for this), appends, returns a 303 redirect to `/`.
- A single `StyleSheet` served via `doc.style(href="/style.css", sheet=...)` to exercise the auto-served-CSS path.

**Concretely stresses.**
- `@app.view` for GET routes.
- Native FastAPI `@app.api.post` for form-driven mutation (a deliberate signal: violetear doesn't yet have a first-class form-POST helper, and that's fine for SSR — FastAPI is right there).
- `doc.style(href=..., sheet=...)` registering an auto-served stylesheet route.
- Multiple `<form>` / `<input>` / `<button>` elements via the markup builder.

**Verification.** Test boots app via `TestClient`; GET `/` returns 200 with the empty-state markup; POST `/entries` with form data returns 303; subsequent GET shows the new entry.

### 03 — Unit converter (`03_interactive.py`)

**Domain.** A length converter with three live-linked inputs (meters, feet, inches). A "mode" toggle switches between *quick* (client-only arithmetic) and *precise* (server RPC that returns a high-precision result). Last-used values restored on reload via `violetear.storage`.

**Shape.**
- `@app.local @dataclass class UiState: meters: float = 1.0; feet: float = 3.28; inches: float = 39.37; mode: str = "quick"`.
- Three `@app.client.callback async def on_*_change(event)` handlers — each reads its own input, computes the others, mutates the proxy (which auto-syncs the DOM via `data-bind-value`).
- `@app.server.rpc async def precise_convert(meters: float) -> dict` — returns `{"feet": …, "inches": …}` with deliberately more decimal places.
- `@app.client.on("ready") async def restore():` — reads `store.last_state` if present and writes it back into `UiState`.
- Single `@app.view("/")` returning the page.

**Concretely stresses.**
- `@app.local` reactive proxy mutated from client.
- `data-bind-value` on the inputs (SSR-rendered, hydrated).
- Multiple `@app.client.callback`s on different events.
- `@app.client.on("ready")` lifecycle hook.
- `@app.server.rpc` with float arguments + dict return.
- `violetear.storage.store` round-trip.
- `violetear.dom.DOM.find(...)` for any direct DOM lookups needed.

**Verification.** Test asserts SSR markup contains `data-bind-value="UiState.meters"` etc., the bundle compiles, and POSTing to `/_violetear/rpc/precise_convert` returns the expected dict.

### 04 — Pomodoro timer (`04_pwa.py`)

**Domain.** A pomodoro timer with three modes (work 25m / short break 5m / long break 15m), session counter, and start/pause/reset controls. State persists across reload (so refreshing mid-session resumes correctly). Installable as a PWA; works offline once the bundle is cached.

**Shape.**
- `app = App(title="Pomodoro", version="1.0.0")` — version pinned (PWA needs a stable version per `README.md`; otherwise the SW re-downloads on every restart).
- `@app.local @dataclass class PomodoroState: mode: str = "work"; seconds_left: int = 1500; running: bool = False; sessions: int = 0`.
- `@app.client.on("ready")` — restore from `store.pomodoro`. If `running` was `true`, set it back to `false` (pause on reload — simpler than computing elapsed wall-time, and a familiar UX). User clicks "start" to resume from `seconds_left`.
- `@app.client` (non-callback, plain client function) `async def tick():` — loops while `PomodoroState.running` is true, decrementing `seconds_left` each second via `asyncio.sleep(1)`, mutating the proxy (auto-DOM-update), and writing to `store.pomodoro` on each tick.
- `@app.client.callback`s for `start`, `pause`, `reset`, `switch_mode`.
- `@app.view("/", pwa=Manifest(name="Pomodoro", short_name="🍅", theme_color="#dc2626", ...))`.

**Concretely stresses.**
- `@app.view` with a custom `Manifest` object.
- Service Worker asset caching (the bundle + the stylesheet get cached).
- `violetear.storage.store` written every second (validates the round-trip-on-mutation pattern).
- A long-running `asyncio` loop on the client side (validates that Pyodide-side concurrency works).
- `@app.local` mutation from a non-callback client function.

**Verification.** Test asserts the manifest endpoint serves the expected JSON (name, theme_color, scope = `/`), the SW endpoint serves a script that lists the bundle URL in its assets list, the bundle compiles.

### 05 — Chat room with presence (`05_realtime.py`)

**Domain.** A chat room. Anyone who connects picks a display name; all messages broadcast to everyone; a sidebar shows who is online; join/leave events appear in the chat as system messages.

**Shape.**
- Module-level state:
  - `messages: list[dict] = []`  — `{from: str, text: str, ts: float}`
  - `users: dict[str, str] = {}` — `client_id → display_name`
- `@app.server.on("connect") async def join(client_id):` — adds entry to `users` (initial name = `"anon-<short>"`), broadcasts a "user joined" system message, calls `set_user_list.broadcast(...)`.
- `@app.server.on("disconnect") async def leave(client_id):` — removes from `users`, broadcasts "user left" + new list.
- `@app.server.realtime async def post_message(text: str, from_id: str):` — appends to `messages`, calls `receive_message.broadcast(...)`.
- `@app.server.realtime async def set_name(client_id: str, new_name: str):` — updates `users[client_id]`, broadcasts `set_user_list`.
- `@app.client.realtime async def receive_message(msg: dict):` — appends to a chat DOM node.
- `@app.client.realtime async def set_user_list(users: dict):` — re-renders the sidebar.
- `@app.client.on("connect") async def request_history():` — once the WS is up, sends a realtime ping to the server (`request_history`). The server-side `@app.server.realtime async def request_history(client_id):` handler then calls `receive_history.invoke(client_id, messages=..., users=...)` — exercising the targeted reverse-RPC path (vs. the broadcast path used for message fan-out).
- `@app.client.on("ready")` — UI init (focus the input box, etc.).
- `@app.client.callback`s for the "send" button and the "change name" button.

**Concretely stresses.**
- Full WS lifecycle: connect, disconnect, message in both directions.
- Both `.broadcast(...)` and (potentially) `.invoke(client_id, ...)` — the latter for the initial-state push.
- `@app.client.on("connect")` (one of the features we wired in `feat: e32a24b`).
- `@app.server.realtime` *and* `@app.client.realtime` in the same file, exercising the matched-pair pattern.
- Manual server-side shared state — gracefully degraded form of what `@app.shared` will replace.

**Verification.** Test connects two `TestClient.websocket_connect` sessions concurrently; the second client receives the first's join broadcast; sending a message from client A causes client B to receive a `receive_message` envelope with the right shape.

## File conventions

- **Naming.** `examples/0N_<slug>.py`. Numeric prefix → sort order matches tier order. Slug is one or two words.
- **Top-of-file docstring** — 5–10 lines:
  - What this example demonstrates (tier + key features).
  - How to run it (`python examples/0N_*.py`).
  - For tiers 2–5: the URL to open in a browser.
  - For tier 5: how to test multi-user (open two tabs).
- **No shared helpers.** Every example is self-contained. If two examples need the same utility, both inline it.
- **Inline comments kept light.** The file should read end-to-end without commentary — code structure does most of the explaining. One-line comments only at non-obvious moments. (Deep pedagogical docs are a separate later effort.)
- **Imports at module top.** No lazy imports inside functions, except where required by the Pyodide/server split (`from violetear.dom import DOM` inside a `@app.client.*` function is the established pattern and is correct).
- **`if __name__ == "__main__":`** at the bottom: tier 1 writes files; tiers 2–5 call `app.run()` (uvicorn).

## Disposition of existing examples

Delete all 9 in a single commit when the first new example lands:

```
basic_pwa.py    broadcast.py    full_pwa.py
hello_world.py  quickstart.py   reactivity.py
rpc_call.py     server_realtime.py  simple_client.py
```

Rationale: a transitional `_legacy/` directory adds clutter without value — the git history is the archive. The new set replaces the old completely.

(Note: the `examples/reactivity.py` was the source of the `class_name=` bug surfaced in slice 1 and fixed in `540a354`. Deleting it removes any lingering reference to the broken pattern.)

## Test strategy

Add `tests/test_examples_canonical.py` with **one thin smoke test per example**. Goal: catch regressions when the framework changes, not to validate the examples' *behavior* in depth (that's what the example itself demonstrates by running).

Each test:
- Imports the example module (top-level execution must succeed — exposes any module-load bug immediately).
- For tier 1: invokes the build function and asserts the output strings contain expected markers.
- For tiers 2–5: builds a `TestClient(example_module.app.api)`, exercises one happy-path request, asserts on key markers (right HTML, right manifest, right WS envelope shape).

Total cost: roughly 5 small tests, ~150 lines combined.

## Build order

Build one example at a time, in numerical order. After each:

1. The file lands.
2. The smoke test lands.
3. `make` (= `make test-unit`) is green locally.
4. Commit: `feat(examples): canonical 0N_<slug> — <one-line description>`.
5. Push so CI runs on each commit (catches Python-3.13-only issues early).

After the last example lands, in a final commit:
- Remove the 9 legacy files.
- Update `README.md`'s quickstart to reference the new canonical examples (1-line nudge: "See `examples/01_static.py` … `examples/05_realtime.py` for canonical demos.").
- Update `AGENTS.md`'s "Common workflows" to point at the canonical set.

## Open decision points (call out anything to flip)

- **Test strategy: thin smoke tests vs runnable-only?** Recommendation above is thin tests. Alternative: examples are demos, not test fixtures; you run them manually when developing. Lean toward tests because uncovered examples *will* bit-rot.
- **Tier-1 output location.** Currently writes alongside the script (`examples/01_static.html`). Alternative: `examples/_out/` directory. Lean toward alongside for "open it and see" simplicity.
- **Tier-5 initial state push** — *resolved in-spec.* Pattern: client `@app.client.on("connect")` sends a realtime ping to the server; server-side `@app.server.realtime` handler responds with `.invoke(client_id, ...)`. This exercises both directions in one flow (client realtime + server reverse-RPC-targeted). Mentioning here so any reader who expects "client GETs a /history endpoint" knows we deliberately avoided HTTP for the initial push.

## Non-decisions (locked in upstream)

- 5 examples, not 6 (no separate `@app.shared` example until the feature ships).
- Independent showcases, not cumulative.
- Per-example domains as listed (design tokens / guestbook / unit converter / pomodoro / chat).
- Examples are removed wholesale; no `_legacy/` transition directory.
- Spec lives at `issues/6-...md` per repo convention (not `docs/superpowers/specs/...`).
