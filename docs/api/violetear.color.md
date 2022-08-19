# Colors



```python linenums="2"
import colorsys
from typing import List

from .units import Unit
```

## The `Color` class

<a name="ref:Color"></a>

```python linenums="7"
class Color:
    def __init__(
        self, red: int = 0, green: int = 0, blue: int = 0, alpha: float = 1.0
    ) -> None:
        self.r = red
        self.g = green
        self.b = blue
        self.a = 1.0 if alpha is None else alpha

    def __str__(self):
        return f"rgba({self.r},{self.g},{self.b},{self.a})"
```

### Conversion methods

#### `Color.from_hsv`



```python linenums="20"
    @classmethod
    def from_hsv(
        cls, hue: float, saturation: float, value: float, alpha: float = 1.0
    ) -> "Color":
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        return Color(int(r * 255), int(g * 255), int(b * 255), alpha)
```

#### `Color.from_hls`



```python linenums="27"
    @classmethod
    def from_hls(
        cls, hue: float, lightness: float, saturation: float, alpha: float = 1.0
    ) -> "Color":
        r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
        return Color(int(r * 255), int(g * 255), int(b * 255), alpha)
```

#### `Color.from_rgb`



```python linenums="34"
    @classmethod
    def from_rgb(cls, red: float, green: float, blue: float, alpha: float = 1.0):
        return Color(int(red * 255), int(green * 255), int(blue * 255), alpha)
```

#### `Color.to_hsv`



```python linenums="38"
    def to_hsv(self):
        return colorsys.rgb_to_hsv(self.r / 255, self.g / 255, self.b / 255)
```

#### `Color.to_hls`



```python linenums="41"
    def to_hls(self):
        return colorsys.rgb_to_hls(self.r / 255, self.g / 255, self.b / 255)
```

#### `Color.to_rgb`



```python linenums="44"
    def to_rgb(self):
        return self.r / 255, self.g / 255, self.b / 255
```

### Color manipulation methods

#### `Color.saturated`



```python linenums="48"
    def saturated(self, saturation: float) -> "Color":
        h, _, v = self.to_hsv()
        return Color.from_hsv(h, saturation, v, self.a)
```

#### `Color.lit`



```python linenums="52"
    def lit(self, lightness: float) -> "Color":
        h, _, s = self.to_hls()
        return Color.from_hls(h, lightness, s, self.a)
```

#### `Color.transparent`



```python linenums="56"
    def transparent(self, alpha: float) -> "Color":
        return Color(self.r, self.g, self.b, alpha)
```

#### `Color.palette`



```python linenums="59"
    @staticmethod
    def palette(start: "Color", end: "Color", steps: int, space="hls") -> List["Color"]:
        from_space = getattr(Color, f"from_{space}")
        to_space = getattr(Color, f"to_{space}")

        start_values = to_space(start)
        end_values = to_space(end)
        step_values = [
            list(Unit.scale(float, s, e, steps))
            for s, e in zip(start_values, end_values)
        ]

        return [from_space(*tuple) for tuple in zip(*step_values)]
```

## Color shortand methods

### `red`

<a name="ref:red"></a>

```python linenums="74"
def red(lightness: float = 1.0) -> Color:
    return Color(255, 0, 0, 1).lit(lightness)
```

### `green`

<a name="ref:green"></a>

```python linenums="77"
def green(lightness: float = 1.0) -> Color:
    return Color(0, 255, 0, 1).lit(lightness)
```

### `blue`

<a name="ref:blue"></a>

```python linenums="80"
def blue(lightness: float = 1.0) -> Color:
    return Color(0, 0, 255, 1).lit(lightness)
```

### `gray`

<a name="ref:gray"></a>

```python linenums="83"
def gray(lightness: float = 1.0) -> Color:
    return Color(255, 255, 255, 1).lit(lightness)
```

