"""
`violetear` is a full-stack Python web framework.

Write server-side rendering, client-side logic, and CSS all in Python.
Client-side functions are compiled to JavaScript at server startup via an
AST compiler — no Pyodide, no WASM, no 14MB download.
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

__version__ = "1.4.0"
