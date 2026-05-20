---
number: 7
title: "Framework rough edges surfaced during canonical-examples build"
state: open
labels:
---

# Framework rough edges surfaced during canonical-examples build

Running log of small framework limitations and ergonomic friction discovered while building the canonical examples (see [[6-canonical-examples-design]]). Per that spec's policy, the build continues; gaps land here as a backlog rather than blocking forward progress.

## 7.1 — Selector parser has no descendant combinator

**Tier(s):** 01

**Symptom.** `sheet.select("section.tokens h2")` raises `ValueError: Invalid CSS selector`. Only compound selectors (tag + classes + id + pseudo) are accepted by `Selector.parse` in `violetear/selector.py`. Workaround in the example: use only flat class selectors (`.tokens-heading` instead of `section.tokens h2`).

**Where to fix.** `violetear/selector.py` — the `SELECTOR` regex matches one compound; would need a top-level grammar that handles whitespace-separated descendants (and ideally `>` child, `+` adjacent, `~` general sibling). Probably a few dozen lines.

**Impact.** Cascading CSS authoring is awkward — every nested element needs a unique class name. For tiny examples this is fine; for a real app it'd push you toward Atomic CSS or component-scoped class explosion.

## 7.2 — `ElementSet.spawn(iterable, tag)` argument naming is misleading

**Tier(s):** 01

**Symptom.** Looking at the signature `spawn(count, tag)` plus the markup.py implementation, when you pass an iterable instead of an int, each *item* becomes the "index" passed to `.each(fn)`. The first dispatched subagent wrote `def _populate_swatch(i, el): color = PALETTE[i]` — natural assumption from the param name, but actually `i` is the Color itself.

**Where to fix.** Two options:
- Rename `count` parameter to `count_or_items` and document the dual behavior, OR
- Add a separate `spawn_from(iterable, tag)` method that's explicit about the item-iteration variant.

**Impact.** Confusing for new users. The fluent `.each(lambda item, el: ...)` form is clean once you know the rule.

## 7.3 — `Element.div().span(...)` chaining stops at the parent

**Tier(s):** 01

**Symptom.** `row.div(classes="type-sample").span(text=...)` raises `AttributeError: 'Element' object has no attribute 'span'`. Tag-method chaining (`div`, `span`, `h1`, etc.) lives on `ElementBuilder`, not on `Element`. To add a child element you either need a `with element as builder:` scope, or `element.add(HTML.span(...))`.

**Where to fix.** This may be intentional API design — Element + ElementBuilder is a deliberate split. But fluent users expect chained children to "just work". Could be addressed by:
- Adding the tag methods to `Element` directly (most natural), OR
- Returning `ElementBuilder(new_element)` from `tag()` methods instead of the raw Element, so chaining keeps working.

**Impact.** Trips up new users; forces a context-manager-or-`HTML.*` pattern that's slightly more verbose than necessary.

## 7.5 — Bundle generator's `inspect.getsource` breaks for dynamically-loaded modules

**Tier(s):** 03 (smoke-test infrastructure)

**Symptom.** When an example module is loaded via `importlib.util.spec_from_file_location` *without* being inserted into `sys.modules` first, the bundle endpoint (`/_violetear/bundle.py`) raises `TypeError: <class 'mod.UiState'> is a built-in class` from `inspect.getsource(cls)` in `App._generate_bundle`. Tier 2 (`02_ssr`) didn't surface this because it has no `@app.local` state classes. Tier 3 hits it as soon as the test fetches the bundle.

**Workaround.** In the smoke-test loader, register the module in `sys.modules` before `spec.loader.exec_module(module)`. (Already applied in `tests/test_examples_canonical.py::_load`.)

**Where to fix in the framework.** At `@app.local` / `client.register_state` time, snapshot `inspect.getsource(cls)` and cache the source string on the registered class. At bundle-emit time, prefer the cached source over re-calling `inspect.getsource`. Same pattern for `client.code_functions`. Alternative: have `register_state` accept an explicit `source=` override for callers who know they're in a dynamic-load context.

**Impact.** Mostly bites test infrastructure and any future "import an example dynamically" tooling. End-user apps with module-level definitions are unaffected.

## 7.4 — `Element.attrs(**kwargs)` doesn't strip trailing underscores

**Tier(s):** 02

**Symptom.** Calling `.attrs(for_="name")` renders `for_="name"` (with trailing underscore) in the HTML, not `for="name"`. Same would apply to any HTML attribute whose name collides with a Python keyword (`class`, `for`, `type` is fine, `is`, etc.). Workaround in tier 2: use the nested `<label>text<input/></label>` pattern, which doesn't need a `for=` attribute.

**Where to fix.** `violetear/markup.py:Element._render` — when iterating `self._attrs`, transform the key with something like `key = key.rstrip("_") if key != "_" else key` before writing the attribute. Same logic could also live in `Element.attrs()` and the `__init__` kwargs sink — pick one to be the canonical normalization point. Note that gap 7.3-adjacent: `Element.__init__` already handles `class_name` → `classes` aliasing manually; a generic underscore-strip would be consistent.

**Impact.** Reference examples can't use `for=` / `class=` via kwargs without producing invalid HTML. Subtle because the form still submits (browsers ignore unknown attrs), so the bug is silent until someone inspects the rendered HTML.

---

Add entries here as more examples land.
