# violetear

![PyPI](https://img.shields.io/pypi/v/violetear)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/violetear)
![PyPI - License](https://img.shields.io/pypi/l/violetear)
[![Documentation](https://github.com/apiad/violetear/actions/workflows/pages.yml/badge.svg)](https://apiad.net/violetear)

> A minimalist CSS generator

`violetear` is a minimalist CSS generator in Python. You write Python code and obtain a CSS definition, that you can either render to a file and serve statically, inject dynamically into your HTML, or use as inline styles directly in your markup.

## Why?

For fun, mostly... but also, because CSS is boring and repetitive. As a style language, CSS is great at describing the most varied designs. However, in terms of productivity, CSS lacks three core features that make programming languages useful: abstraction, encapsulation, and reusability.

Using a general-purpose programming language to generate CSS we can obtain the best of both worlds: the expresivity of a declarative with the productivity of an imperative language.

## What?

`violetear` is a bridge between Python and CSS. The simplest use case is a fluid API for generating CSS, full with code completion, documentation, and shorthand methods for the most common CSS rule sets, including [flexbox and grid layouts](https://apiad.net/violetear/guide/#layout-options).

But it gets better quickly. Using `violetear` you can [compose simpler styles into more complex ones](https://apiad.net/violetear/guide/#simple-styling), reusing common rules to reduce repetition to a minimum. This way you can build up complex layouts via composition.

You can manipulate magnitudes, such as colors and font-sizes, making it much easier to [generate a specific color palette](https://apiad.net/violetear/guide/#playing-with-colors), for instance. Since you have a full-featured programming language, you can leverage variables and methods to, for example, generate dynamic themes on-the-fly based on user-defined preferences.

Finally, `violetear` can generate only the subset of styles used in any given template from a single Pyhon source. This means you can happily define all your styles globally and then deliver the minimum CSS subset necessary for each view.

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

And you can style specific states:

```python
title.on("hover").font(weight="bolder")
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

See the full user guide at <https://apiad.net/violetear/guide/>.

## Contribution

License is MIT, so all contributions are welcome!

The easiest way to contribute is simply by installing the library, using it to build some style you want, and then open an issue telling me what was hard or impossible for you to do. This will help me decide what to prioritize, since CSS is damn huge!

Likewise, if you're feeling adventurous, go ahead and add some fluid methods to the `violetear.style.Style` class to cover new CSS rules, and then open a PR.

## Roadmap

**Desired features**

- Cover all basic CSS rules.
- Docs!
- Support for grid layouts with helper methods
- Support transitions with helper methods to create animation curves

**0.6**

- Changed `Color.palette` method name
- Support for `visibility: hidden`

**0.5.1**

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
