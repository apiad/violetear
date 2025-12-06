"""`violetear` is a minimalist CSS generator.

You use Python to define CSS styles and automatically obtain a CSS stylesheet.
Using a fluent API, you can quickly build complex styles programmatically
and compose them into a fully-fledged design system.
"""

from .stylesheet import StyleSheet
from .style import Style
from .selector import Selector
from .units import Unit
from .color import Color


__version__ = "0.13.0"
