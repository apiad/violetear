??? note "Docstring"
    `violetear` is a minimalist CSS generator.
    
    You use Python to define CSS styles and automatically obtain a CSS stylesheet.
    Using a fluent API, you can quickly build complex styles programmatically
    and compose them into a fully-fledged design system.


This is the main module of `violetear`.
We'll import the main classes so they can be used directly.

The [`StyleSheet`](../violetear.stylesheet.StyleSheet/#ref:) class
represents a collections of styles (think, a CSS file).



```python linenums="11"
from .stylesheet import StyleSheet
```

The [`Style`](../violetear.style/#ref:Style) class represents a single style.



```python linenums="13"
from .style import Style
```

The [`Selector`](../violetear.selector/#ref:Selector) class representes a CSS selector.



```python linenums="15"
from .selector import Selector
```

The [`Unit`](../violetear.units/#ref:Unit) class represents a magnitude, whether pixels, points, etc.



```python linenums="17"
from .units import Unit
```

The [`Color`](../violetear.color/#ref:Color) class represents a CSS color.



```python linenums="19"
from .color import Color
```

