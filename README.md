# violetear

![PyPI](https://img.shields.io/pypi/v/violetear)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/violetear)
![PyPI - License](https://img.shields.io/pypi/l/violetear)

> A minimalist CSS generator

`violetear` is a minimalist CSS generator in Python. You write Python code and obtain a CSS definition, that you can either render to a file and serve statically, or inject dynamically into your HTML, or use inline styles directly in your markup.

It is a pure Python package with zero dependencies. Install with:

```bash
pip install violetear
```

## Why?

For fun, mostly... but also, because CSS is boring and repetitive. But using a full-featured programming language allows me to unlock orders of magnitude of productivity generating styles programatically.

Using `violetear` you can compose simpler styles into more complex ones, reusing common rules to reduce repetition to a minimum. You can manipulate magnitudes, such as colors, making it much easier to generate a specific color pallete, for instance. Since you have a full-featured programming language, you can leverage variables and methods to, for example, generate dynamic themes on-the-fly based on user-defined colors.

Finally, with `violetear` you can generate only the subset if styles you end up using in any given template from a single Pyhon source. This means you can happily define all your styles globally and then deliver the minimum CSS subset necessary for each view.
