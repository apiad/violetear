# violetear

![PyPI](https://img.shields.io/pypi/v/violetear)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/violetear)
![PyPI - License](https://img.shields.io/pypi/l/violetear)
[![Tests](https://github.com/apiad/violetear/actions/workflows/tests.yml/badge.svg)](https://github.com/apiad/violetear/actions/workflows/tests.yml)
[![Documentation](https://github.com/apiad/violetear/actions/workflows/docs.yml/badge.svg)](https://apiad.net/violetear)

> A minimalist CSS generator

`violetear` is a minimalist CSS generator in Python. You write Python code and obtain a CSS definition, that you can either render to a file and serve statically, inject dynamically into your HTML, or use as inline styles directly in your markup.

## Why?

For fun, mostly... but also, because CSS is boring and repetitive. As a style language, CSS is great at describing the most varied designs. However, in terms of productivity, CSS lacks three core features that make programming languages useful: abstraction, encapsulation, and reusability.

Using a general-purpose programming language to generate CSS we can obtain the best of both worlds: the expresivity of a declarative language like CSS with the productivity of an imperative language like Python.

## What?

`violetear` is a bridge between Python and CSS. It gives you a fluent API to generate CSS styles, full with code completion, documentation, and shorthand methods for the most common CSS rule sets. Some of the things you can do with `violetear` easily are:

- [Create CSS styles from Python code](https://apiad.net/violetear/guide/#simple-styling) using a fluent, fully documented API that covers the most common rules.
- [Generate CSS stylesheets programatically](https://apiad.net/violetear/guide/#creating-styles-programatically), which means you can create several related styles with ease using loops and parameters.
- [Manipulate magnitudes and colors](https://apiad.net/violetear/examples/color-spaces) to create custom color palettes.
- [Generate minimal CSS files](#) including only the subset of rules that are used in a given template.
- [Create complex layouts using flexbox and grid](https://apiad.net/violetear/examples/fluid-grid) programatically with very few lines of code.
- [Generate a semantic design system on-the-fly](https://apiad.net/violetear/examples/semantic-inputs) complete with typographic styles and different buttons classes.
- [Define transitions and animations](https://apiad.net/violetear/examples/animations) in a modular way.

And much more... When you combine a full-flegded programming language with powerful abstractions and carefully designed APIs, your imagination is the only limit.

## How?

`violetear` is a pure Python package with zero dependencies. Install it with:

```bash
pip install violetear
```

Next, create a stylesheet:

```python
from violetear import StyleSheet

sheet = StyleSheet()
```

Then you add your styles using common CSS selectors and a fluid API to quickly build complex rule sets:

```python
title = sheet.select("#title").font(14, weight="lighter").margin(5, top=0)
subtitle = sheet.select(".subtitle").apply(title).font(12)
```

You can add conditional (media query) styles with a simple API:

```python
with sheet.media(min_width=768):
    sheet.redefine(title).display("inline")
```

You can style specific states and add animations easily:

```python
title.transition(timing="ease-in-out").on("hover").font(weight="bolder")
```

You can add custom rules for rare cases when `violetear` doesn't have a shorthand method:

```python
subtitle.rule("hyphens", "auto")
```

Or a bunch of them all at once (`_` are converted to `-` automatically):

```python
subtitle.rules(
    text_decoration_color=Colors.SandyBrown,
    text_decoration_style="dashed",
)
```

And finally `violetear` has a few ready-made collection of styles for some of the most common design patterns. Here's a [12-column grid system made with flexbox](https://apiad.net/violetear/api/violetear.presets#flex-based-grid-system) with varying screen sizes that is completely customizable in just 5 lines of code:

```python
from violetear.presets import FlexGrid

sheet.extend(FlexGrid(
    columns=12,        # 12 columns by default
    breakpoints=dict(
        lg=(1600, 8),  # Add several breakpoints at different
        md=(1200, 6),  # screen sizes changing the
        sm=(800, 4),   # number of columns and adding custom
        xs=(400, 1)    # classes for extra responsiveness
    )
))
```

And here's a [semantic design with typography and button styles](https://apiad.net/violetear/api/violetear.presets#semantic-input-system)  like `.text.md` and `.btn.primary` that is also completely customizable:

```python
from violetear.presets import SemanticDesign

sheet.extend(SemanticDesign(
    sizes=dict(sm=1.0, md=1.5, lg=2.0),
    colors=dict(
        normal=Colors.White.lit(0.8),
        primary=Colors.Blue.lit(0.4),
        success=Colors.Green.lit(0.4),
        error=Colors.Red.lit(0.4),
    )
).all())
```

Once your stylesheet is complete, you have a few options to deliver the styles to your frontend.

You can render the stylesheet into a static file:

```python
sheet.render("static/css/main.css")
```

You can embed it into your HTML (e.g, using Jinja):

```jinja
<style>
    {{ style.render() }}
</style>
```

You can use inline styles:

```jinja
<h2 {{ style.subtitle.inline() }}>Subtitle</h2>
```

Or you can automatically add the corresponding selector attributes to a given tag:

```jinja
<h2 {{ style.subtitle.markup() }}>Subtitle</h2>
<!-- Becomes -->
<h2 class="subtitle">Subtitle</h2>
```

## Documentation

To learn more, you can:

- Read the introductory [user guide](https://apiad.net/violetear/guide) that showcases the main functionalities of the library.
- Browse the [examples](https://apiad.net/violetear/examples) to see concrete and detailed use cases.
- Read the [fully annotated API](https://apiad.net/violetear/api/violetear) to understand the inner workings of the library.

## Contribution

License is MIT, so all contributions are welcome!

The easiest way to contribute is simply by installing the library, using it to build some style you want, and then open an issue telling me what was hard or impossible for you to do. This will help me decide what to prioritize, since CSS is damn huge!

Likewise, if you're feeling adventurous, go ahead and add some fluid methods to the [`violetear.style.Style`](https://apiad.net/violetear/api/violetear.style/#the-style-class) class to cover new CSS rules, and then open a PR.

## Roadmap

Right now `violetear` is in pre-release mode, which means the API is completely unstable. When it reaches a reasonable level of maturity, we will release a `v1.0` and stabilize the API.

**v1.0 milestone checklist**

- [ ] Fluent methods for most relevant CSS rules
- [ ] Fully documented API
- [ ] Examples for all relevant use cases
- [ ] Fully typed method signatures
- [ ] Full check of argument values and rule attributes
- [ ] Dynamic generation of CSS based on HTML parsing as well as attribute lookup
- [ ] Parameterized presets for relevant design systems
- [ ] Transitions and animations with helper methods to create timing curves
- [x] Grid and flexbox styles
- [x] Definitions for all CSS colors
- [x] Creating and manipulating color palettes
- [x] Creating scales in any unit
- [x] States
- [x] Media queries

**v0.10.2**

- Support multiple animations in a single element.

**v0.10.1**

- Add support for CSS animations.

**v0.10.0**

- Basic support for transitions and transforms.

**v0.9.0**

- Add `StyleSheet.extend` to extend stylesheets with presets
- Add `FlexGrid` to create flexbox grids easily

**v0.8.1**

- Add color palettes with generator methods to `Colors`.
- Add example with color functionality.

**v0.8.0**

- Improved color space conversion in the `Color` class
- Refactor a bunch of color methods
- Added methods to tweak colors
- Added all CSS colors to `violetear.color.Colors`.

**v0.7.0**

- Support for grid layouts with helper methods

**v0.6**

- Changed `Color.palette` method name
- Support for `visibility: hidden`

**v0.5.1**

- Improved support for flexbox

**v0.5**

- Support for color palettes
- Basic flexbox layout

**v0.4.1**

- Add min/max width and height
- Create scales of a given unit (e.g., font sizes)
- Better support for sub-styles (e.g, `:hover`)
- Support for `text-align: center`

**v0.4**

- Support for custom states with the `on` method.

**v0.3**

- Support for media queries via context managers

**v0.2**

- Refactored style API
- Added support for basic CSS selectors

**v0.1**

- Basic API
