"""`violetear` is a minimalist CSS generator.

You use Python to define CSS styles and automatically obtain a CSS stylesheet.
Using a fluent API, you can quickly build complex styles programmatically
and compose them into a fully-fledged design system.
"""

from .style import Style
from .stylesheet import StyleSheet
from .units import Unit
from .color import Color
from .selector import Selector
