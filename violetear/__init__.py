"""
`violetear` is a minimalist CSS generator.

You use Python to define CSS styles and automatically obtain a CSS stylesheet.
Using a fluent API, you can quickly build complex styles programmatically
and compose them into a fully-fledged design system.
"""

from .stylesheet import StyleSheet
from .style import Style
from .selector import Selector
from .units import Unit
from .color import Color
from .markup import Document, Element, Component, HTML

# New Framework export (lazy import to avoid hard dependency errors if possible,
# though our App class handles the check internally)
try:
    from .app import App
    from .pwa import Manifest
except ImportError:
    pass

__version__ = "1.2.3"
