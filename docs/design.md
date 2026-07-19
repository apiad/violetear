# Design philosophy

This document describes the design philosophy of `violetear`. You can read it if you want to understand why we made the choices we made. But also, if you're thinking about contributing (and we'd love you to) then this document will help you find the right mindset to work in tandem the existing codebase.

The design of `violetear` is based on a few simple principles that we hope will resonate with your own values.
Our purpose is to build a low-level library for generating HTML and CSS that can serve as a foundation for more complex and domain-specific frameworks, while being feature-rich enough to support a reasonable level of its users needs.

These are the core principles that guide our design.

## Unopinionated

`violetear` is a library, not a framework. It will never attempt to dictate the correct way to structure a web application, or even a single HTML or CSS file. In principle, everything that is valid HTML and CSS should be equally feasible to achieve through `violetear`.

## Modular

`violetear` is a set of tools for generating HTML and CSS. You should be able to use any of these tools independently or in unison. For example, you can use the `StyleSheet` and `Document` classes to create full-fledged web pages, you can also use a single `Element` or `Style` instance and inject it into a template.

## Lightweight

`violetear` aims to have zero dependencies outside Python's standard library. It is a lightweight library that can always be added to any existing project without causing any conflicts with other dependencies.

## Pythonic

`violetear` strives for a terse, pythonic syntax that requires the least amount of effort to get things done, as long as it doesn't hurt readibility to an unreasonable level. There should be a simple, explicit, and preferably unique way of doing everything.

## Type-safe

`violetear` aims to be fully typed in a way that's compatible with the most common Python type checkers. Also, type annotations should be leveraged to provide the best developer experience possible when using a sufficiently sophisticated editor.

## Comprehensive

`violetear` aims to cover a majority of the most relevant use cases. That means including shorthand methods for the most common CSS properties and HTML attributes.

## Batteries included

`violetear` will include presets for the most common design patterns, such as semantic designs, utility classes, flex and grid layouts, etc. However, this should be in tandem with our unopinionated philosophy, so these presets will not force you into any specific design style.

## Leaky abstractions

`violetear` will never be able to cover the full range of the CSS specification, though. So it will always let you sneak under the abstraction (e.g., using `Style.rules`) to bypass its abstractions and directly mess with the underlying HTML and CSS structure. This way, anything that can't be done in a pythonic way with `violetear` will still be possible with lower-level abstractions.

## State management: the dataclass as source of truth

Violetear's state model is built on one idea: **a Python `@dataclass` is the canonical definition of state**. Both client-side local state (`@app.local`) and cross-client shared state (`@app.shared`) use the same primitive — a plain dataclass — and the framework generates the correct reactive glue automatically.

### @app.local — per-session reactive state

`@app.local` compiles a dataclass to a JS reactive singleton. Field assignments inside `@app.client` functions automatically update every DOM element bound to that field. No stores, no signals, no event emitters. The dataclass is the store.

### @app.shared — server-authoritative broadcast state

`@app.shared` extends the same pattern across all connected clients. The dataclass instance lives on the server (in `SharedRegistry`). Any field assignment — whether from server-side code or a client `@app.client.callback` — is intercepted by `SharedProxy.__setattr__`, which broadcasts a `shared_sync` frame to every WebSocket connection.

Key design decisions:

- **Last-write-wins, field-level replacement.** There is no merge logic. A field assignment replaces the current value. This is the correct default for most UI state; richer semantics (shared lists with append-only ops, CRDTs) are a later abstraction layer.
- **Server is the source of truth.** When a client writes a shared field, the write goes to the server first (`shared_set`), the server validates and re-broadcasts (`shared_sync`) to all clients including the sender. The client never applies a change locally before the server confirms it. This makes conflicts trivially impossible at the cost of one RTT per mutation.
- **`server_only` fields** allow the server to own a field exclusively. Clients can read the value (they receive `shared_sync` for it) but their `shared_set` frames are rejected. The transpiler strips the `_shared.set()` call from the emitted setter for these fields.
- **Late-joiner push.** On every new WebSocket connection, the server pushes one `shared_sync` frame per field per class before yielding to the application's `on("connect")` handler. New clients arrive with full state.
- **`_shared._receiving` flag.** When the client runtime handles an incoming `shared_sync`, it sets a flag that suppresses the reactive setter's outbound `shared_set`. This prevents echo loops without any extra coordination.

### When to use which

| | `@app.local` | `@app.shared` |
|---|---|---|
| Scope | Per browser tab | All connected clients |
| Lives in | Browser JS singleton | Server `SharedRegistry` |
| Mutation path | Direct setter → DOM | setter → WS → server → broadcast → all DOM |
| Persistence | Optional (`localStorage`) | In-memory (Redis in future) |
| Conflict model | N/A (isolated) | Last-write-wins |
| Use for | UI toggles, filters, per-user form state | Chat, counters, collaborative cursors, leaderboards |

## Partials: fragments as the unit of server-rendered UI

`@app.partial` is the minimal server-side primitive for dynamic UI composition. The design constraint is strict: a partial route returns a raw HTML fragment — no `<html>`, no `<head>`, no injected scripts. The client is responsible for fetching and injecting it.

This keeps the server free of client concerns and keeps partial responses cacheable. The DOM manipulation API (`DOM.find`, `DOM.query`, `el.load()`) provides the client-side half.

### Re-hydration after injection

Injecting raw HTML into the DOM normally breaks reactive bindings — any `data-bind-*` attributes in the fragment are unknown to `ReactiveRegistry`. The solution is `_hydrate_subtree(root, scope)`: a focused hydration pass that runs on the injected subtree rather than the full page. After binding, `ReactiveRegistry.flush_subtree(root)` applies cached reactive values immediately so the fragment reflects current state without waiting for the next state mutation.

The `_violetear_scope` module variable stores the scope from the initial `Violetear_hydrate` call, making it available to `_DOMEl.load()` without threading it through the call chain.

### DOM API design choices

- **OOP, not jQuery**: `DOM.find(id).load(url)` reads like a sentence. Chaining works because every method returns `this`.
- **Method vs property for `html`**: `el.html(content)` is a method (not a property setter) to distinguish it semantically from `el.load()`. Both set `innerHTML` but only `load` re-hydrates. The visual distinction matters.
- **No client-side element construction**: `el.append(child_element)` is explicitly out of scope for v1. It requires constructing `Element` trees client-side, which duplicates the server-side `ElementBuilder` API and adds complexity. Partials are the clean alternative: construct the fragment server-side, fetch and inject client-side.
