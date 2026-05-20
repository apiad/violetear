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

---

Add entries here as more examples land.
