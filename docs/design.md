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
