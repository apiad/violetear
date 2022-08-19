"""`violetear` is a minimalist CSS generator.

You use Python to define CSS styles and automatically obtain a CSS stylesheet.
Using a fluent API, you can quickly build complex styles programmatically
and compose them into a fully-fledged design system.
"""

# This is the main module of `violetear`.
# We'll import the main classes so they can be used directly.

# The [`StyleSheet`](ref:violetear.stylesheet.StyleSheet) class
# represents a collections of styles (think, a CSS file).
from .stylesheet import StyleSheet

# The [`Style`](ref:violetear.style:Style) class represents a single style.
from .style import Style

# The [`Selector`](ref:violetear.selector:Selector) class representes a CSS selector.
from .selector import Selector

# The [`Unit`](ref:violetear.units:Unit) class represents a magnitude, whether pixels, points, etc.
from .units import Unit

# The [`Color`](ref:violetear.color:Color) class represents a CSS color.
from .color import Color
