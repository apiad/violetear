# # Colors

"""This module defines the `Color` class with methods to create and manipulate
colors in different spaces. It also defines all common CSS colors, and utilities
to combine them.
"""

# Basic imports

import colorsys  # for changing color spaces
import sys  # for current byte-order
from binascii import hexlify  # for converting to hexadecimal
from typing import List, Tuple, overload

from .units import Unit

# ## The `Color` class


class Color:
    def __init__(
        self, red: int = 0, green: int = 0, blue: int = 0, *, alpha: float = 1.0
    ) -> None:
        self.r = red
        self.g = green
        self.b = blue
        self.a = 1.0 if alpha is None else alpha

    def __str__(self):
        return f"rgba({self.r},{self.g},{self.b},{self.a})"

    def __repr__(self):
        return f"Color({self.r},{self.g},{self.b}, alpha={self.a})"

    # #### `Color.saturated`

    def saturated(self, saturation: float) -> "Color":
        h, _, v = self.hsv()
        return hsv(h, saturation, v, alpha=self.a)

    # #### `Color.lit`

    def lit(self, lightness: float) -> "Color":
        h, _, s = hls(self)
        return hls(h, lightness, s, alpha=self.a)

    # #### `Color.shifted`

    def shifted(self, hue: float) -> "Color":
        _, l, s = hls(self)
        return hls(hue, l, s, alpha=self.a)

    # #### `Color.transparent`

    def transparent(self, alpha: float) -> "Color":
        return Color(self.r, self.g, self.b, alpha=alpha)

    # #### `Color.redshift`

    def redshift(self, percent: float, *, space="hls") -> "Color":
        _, l, s = hls(self)
        target = hls(0, l, s)
        return self.towards(target, percent, space=space)

    # #### `Color.blueshift`

    def blueshift(self, percent: float, *, space="hls") -> "Color":
        _, l, s = hls(self)
        target = hls(1, l, s)
        return self.towards(target, percent, space=space)

    # #### `Color.towards`

    def towards(self, other: "Color", percent: float, *, space="hls") -> "Color":
        space = dict(rgb=rgb, hls=hls, hsv=hsv)[space]

        start_values = space(self)
        end_values = space(other)
        result = [s + (e - s) * percent for s, e in zip(start_values, end_values)]

        return space(*result)

    # #### `Color.palette`

    @staticmethod
    def palette(
        start: "Color", end: "Color", percents: int, space="hls"
    ) -> List["Color"]:
        percents = Unit.scale(float, 0, 1, percents)
        return [start.towards(end, p, space=space) for p in percents]


# ## Color spaces

# ### `rgb`


@overload
def rgb(red: float, green: float, blue: float, /, *, alpha: float = 1.0) -> Color:
    ...


@overload
def rgb(color: Color, /) -> Tuple[float, float, float]:
    ...


def rgb(*args, **kwargs):
    if isinstance(args[0], Color):
        color = args[0]
        return color.r / 255, color.g / 255, color.b / 255
    else:
        r, g, b = args
        alpha = kwargs.pop("alpha")

        return Color(int(r * 255), int(g * 255), int(b * 255), alpha=alpha)


# ### `hsv`


@overload
def hsv(
    hue: float, saturation: float, value: float, /, *, alpha: float = 1.0
) -> "Color":
    ...


@overload
def hsv(color: Color, /) -> Tuple[float, float, float]:
    ...


def hsv(*args, **kwargs):
    if isinstance(args[0], Color):
        color = args[0]
        return colorsys.rgb_to_hsv(*rgb(color))
    else:
        h, s, v = args
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        alpha = kwargs.pop("alpha")

        return rgb(r, g, b, alpha=alpha)


# ### `hls`


@overload
def hls(
    hue: float, lightness: float, saturation: float, /, *, alpha: float = 1.0
) -> "Color":
    ...


@overload
def hls(color: Color, /) -> Tuple[float, float, float]:
    ...


def hls(*args, **kwargs):
    if isinstance(args[0], Color):
        color = args[0]
        return colorsys.rgb_to_hls(*rgb(color))
    else:
        h, l, s = args
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        alpha = kwargs.pop("alpha", 1.0)

        return rgb(r, g, b, alpha=alpha)


# ### `hex`


@overload
def hex(code: str, /, *, alpha: float = 1.0) -> Color:
    ...


@overload
def hex(color: Color, /) -> str:
    ...


def hex(*args, **kwargs):
    if isinstance(args[0], str):
        code = args[0]
        alpha = kwargs.pop("alpha", 1.0)

        if code.startswith("#"):
            code = code[1:]

        if len(code) == 3:
            r = code[0] * 2
            g = code[1] * 2
            b = code[2] * 2
        else:
            r = code[0:2]
            g = code[2:4]
            b = code[4:6]

        return Color(int(r, 16), int(g, 16), int(b, 16), alpha=alpha)
    else:
        color = args[0]

        r = hexlify(color.r.to_bytes(1, sys.byteorder)).decode("ascii")
        g = hexlify(color.g.to_bytes(1, sys.byteorder)).decode("ascii")
        b = hexlify(color.b.to_bytes(1, sys.byteorder)).decode("ascii")
        return f"#{r}{g}{b}"


# ## Basic color shorthands

# ### `red`


def r(lightness: float = 1.0) -> Color:
    return Colors.Red.lit(lightness)


# ### `green`


def g(lightness: float = 1.0) -> Color:
    return Colors.Green.lit(lightness)


# ### `blue`


def b(lightness: float = 1.0) -> Color:
    return Colors.Blue.lit(lightness)


# ### `gray`


def gray(lightness: float = 1.0) -> Color:
    return Colors.Gray.lit(lightness)


# ## The `Colors` class

# These are the web colors defined in CSS.
# They are defined as class members of the `Colors` class,
# so they can be accessed by dot notation.

# Similarly, the `Colors` class provides an item getter
# to access colors by name.


class Colors:
    """Contains class-member definitions for all standard CSS colors.

    Colors can be accessed by dot notation (`Colors.Lime`) or
    by name (`Colors['Fuchsia']`).
    """

    def __getitem__(self, key):
        return getattr(Color, key)

    # ### Basic web colors
    White = hex("#ffffff")
    Silver = hex("#c0c0c0")
    Gray = hex("#808080")
    Black = hex("#000000")
    Red = hex("#ff0000")
    Maroon = hex("#800000")
    Yellow = hex("#ffff00")
    Olive = hex("#808000")
    Lime = hex("#00ff00")
    Green = hex("#008000")
    Aqua = hex("#00ffff")
    Teal = hex("#008080")
    Blue = hex("#0000ff")
    Navy = hex("#000080")
    Fuchsia = hex("#ff00ff")
    Purple = hex("#800080")

    # ### Pink shades
    MediumVioletRed = hex("#c71585")
    DeepPink = hex("#ff1493")
    PaleVioletRed = hex("#db7093")
    HotPink = hex("#ff69b4")
    LightPink = hex("#ffb6c1")
    Pink = hex("#ffc0cb")

    # ### Red shades
    DarkRed = hex("#8b0000")
    Red = hex("#ff0000")
    Firebrick = hex("#b22222")
    Crimson = hex("#dc143c")
    IndianRed = hex("#cd5c5c")
    LightCoral = hex("#f08080")
    Salmon = hex("#fa8072")
    DarkSalmon = hex("#e9967a")
    LightSalmon = hex("#ffa07a")

    # ### Orange shades
    OrangeRed = hex("#ff4500")
    Tomato = hex("#ff6347")
    DarkOrange = hex("#ff8c00")
    Coral = hex("#ff7f50")
    Orange = hex("#ffa500")

    # ### Yellow shades
    DarkKhaki = hex("#bdb76b")
    Gold = hex("#ffd700")
    Khaki = hex("#f0e68c")
    PeachPuff = hex("#ffdab9")
    Yellow = hex("#ffff00")
    PaleGoldenrod = hex("#eee8aa")
    Moccasin = hex("#ffe4b5")
    PapayaWhip = hex("#ffefd5")
    LightGoldenrodYellow = hex("#fafad2")
    LemonChiffon = hex("#fffacd")
    LightYellow = hex("#ffffe0")

    # ### Brown shades
    Maroon = hex("#800000")
    Brown = hex("#a52a2a")
    SaddleBrown = hex("#8b4513")
    Sienna = hex("#a0522d")
    Chocolate = hex("#d2691e")
    DarkGoldenrod = hex("#b8860b")
    Peru = hex("#cd853f")
    RosyBrown = hex("#bc8f8f")
    Goldenrod = hex("#daa520")
    SandyBrown = hex("#f4a460")
    Tan = hex("#d2b48c")
    Burlywood = hex("#deb887")
    Wheat = hex("#f5deb3")
    NavajoWhite = hex("#ffdead")
    Bisque = hex("#ffe4c4")
    BlanchedAlmond = hex("#ffebcd")
    Cornsilk = hex("#fff8dc")

    # ### Green shades
    DarkGreen = hex("#006400")
    Green = hex("#008000")
    DarkOliveGreen = hex("#556b2f")
    ForestGreen = hex("#228b22")
    SeaGreen = hex("#2e8b57")
    Olive = hex("#808000")
    OliveDrab = hex("#6b8e23")
    MediumSeaGreen = hex("#3cb371")
    LimeGreen = hex("#32cd32")
    Lime = hex("#00ff00")
    SpringGreen = hex("#00ff7f")
    MediumSpringGreen = hex("#00fa9a")
    DarkSeaGreen = hex("#8fbc8f")
    MediumAquamarine = hex("#66cdaa")
    YellowGreen = hex("#9acd32")
    LawnGreen = hex("#7cfc00")
    Chartreuse = hex("#7fff00")
    LightGreen = hex("#90ee90")
    GreenYellow = hex("#adff2f")
    PaleGreen = hex("#98fb98")

    # ### Cyan shades
    Teal = hex("#008080")
    DarkCyan = hex("#008b8b")
    LightSeaGreen = hex("#20b2aa")
    CadetBlue = hex("#5f9ea0")
    DarkTurquoise = hex("#00ced1")
    MediumTurquoise = hex("#48d1cc")
    Turquoise = hex("#40e0d0")
    Aqua = hex("#00ffff")
    Cyan = hex("#00ffff")
    Aquamarine = hex("#7fffd4")
    PaleTurquoise = hex("#afeeee")
    LightCyan = hex("#e0ffff")

    # ### Blue shades
    MidnightBlue = hex("#191970")
    Navy = hex("#000080")
    DarkBlue = hex("#00008b")
    MediumBlue = hex("#0000cd")
    Blue = hex("#0000ff")
    RoyalBlue = hex("#4169e1")
    SteelBlue = hex("#4682b4")
    DodgerBlue = hex("#1e90ff")
    DeepSkyBlue = hex("#00bfff")
    CornflowerBlue = hex("#6495ed")
    SkyBlue = hex("#87ceeb")
    LightSkyBlue = hex("#87cefa")
    LightSteelBlue = hex("#b0c4de")
    LightBlue = hex("#add8e6")
    PowderBlue = hex("#b0e0e6")

    # ### Purple shades
    Indigo = hex("#4b0082")
    Purple = hex("#800080")
    DarkMagenta = hex("#8b008b")
    DarkViolet = hex("#9400d3")
    DarkSlateBlue = hex("#483d8b")
    BlueViolet = hex("#8a2be2")
    DarkOrchid = hex("#9932cc")
    Fuchsia = hex("#ff00ff")
    Magenta = hex("#ff00ff")
    SlateBlue = hex("#6a5acd")
    MediumSlateBlue = hex("#7b68ee")
    MediumOrchid = hex("#ba55d3")
    MediumPurple = hex("#9370db")
    Orchid = hex("#da70d6")
    Violet = hex("#ee82ee")
    Plum = hex("#dda0dd")
    Thistle = hex("#d8bfd8")
    Lavender = hex("#e6e6fa")

    # ### White shades
    MistyRose = hex("#ffe4e1")
    AntiqueWhite = hex("#faebd7")
    Linen = hex("#faf0e6")
    Beige = hex("#f5f5dc")
    WhiteSmoke = hex("#f5f5f5")
    LavenderBlush = hex("#fff0f5")
    OldLace = hex("#fdf5e6")
    AliceBlue = hex("#f0f8ff")
    Seashell = hex("#fff5ee")
    GhostWhite = hex("#f8f8ff")
    Honeydew = hex("#f0fff0")
    FloralWhite = hex("#fffaf0")
    Azure = hex("#f0ffff")
    MintCream = hex("#f5fffa")
    Snow = hex("#fffafa")
    Ivory = hex("#fffff0")
    White = hex("#ffffff")

    # ### Black shades
    Black = hex("#000000")
    DarkSlateGray = hex("#2f4f4f")
    DimGray = hex("#696969")
    SlateGray = hex("#708090")
    Gray = hex("#808080")
    LightSlateGray = hex("#778899")
    DarkGray = hex("#a9a9a9")
    Silver = hex("#c0c0c0")
    LightGray = hex("#d3d3d3")
    Gainsboro = hex("#dcdcdc")

    # ### Extra
    RebeccaPurple = hex("#663399")
