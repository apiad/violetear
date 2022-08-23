# # Styles

"""This module defines the `Style` class.
"""

from __future__ import annotations

# These are for typing our methods:
from typing import List, Tuple, Union, TYPE_CHECKING


# These ones are internal to `violetear`:
from .selector import Selector
from .units import Unit, fr, ms, pc, minmax, rem, repeat, sec
from .types import GridSize, GridTemplate, FontWeight
from .color import Color, Colors, gray
from .helpers import style_method

# This trick is necessary to annotate the `Style.animation` method
# without incurring in cyclic import errors,
# because the `Animation` class does need to import `Style` in runtime.

if TYPE_CHECKING:
    from .animation import Animation

# And this one is for generating CSS:
import textwrap

# ## The `Style` class

# The `Style` class is the main concept in `violetear`.
# It encapsulates the functionality to generate CSS rules.
# In summary, a `Style` is defined by a CSS selector
# (represented in the [`Selector`](ref:violetear.selector:Selector) class)
# and a set of rules, internally implemented with dictionary that maps attributes to values.

# The `Style` class provides a main [`rule`](ref:violetear.style:Style.rule) method to manually set any CSS rule.
# However, to simplify usage, the most common CSS rules are encapsulated in fluent methods
# that allow chained invocation to quickly build a complex style.


class Style:
    def __init__(
        self, selector: Union[str, Selector] = None, *, parent: Style = None
    ) -> None:
        """Create a new instance of `Style`.

        **Parameters**:

        - `selector`: The selector to which this style applies. Can be `None`, or a string,
                      in which case it is parsed with `Selector.from_css`.
        - `parent`: An optional parent style (e.g., if this is an state or children style) so
                    that when checking which styles are used, the parent can be referenced.
        """
        if isinstance(selector, str):
            selector = Selector.from_css(selector)

        self.selector = selector
        self._rules = {}
        self._parent = parent
        self._children = {}
        self._transitions = []
        self._transforms = {}
        self._animations = set()
        self._animation_configs = []

    # ### Basic rule manipulation
    # These methods allows manipulating rules manually.

    # #### `Style.rule`
    # Adds a rule to the internal dictionary. It will be casted to `str` for uniformity.
    # This implies that simple values like `int` and `float` are represented as is,
    # but complex values like `Unit` and `Color` will be converted to their string representation
    # using their corresponding `__str__` methods.

    def rule(self, attr: str, value) -> Style:
        """Define a new CSS rule.

        **Parameters**:

        - `attr`: a CSS attribute (e.g., `'font-size'`)
        - `value`: a value for the attribute. It will be converted to `str` internally.
        """
        self._rules[attr] = str(value)
        return self

    # #### `Style.rules`

    def rules(self, **rules) -> Style:
        """Define a bunch of CSS rules at once with kwargs.

        Attribute names are automatically converted from `snake_case` to `kebab-case`.
        """

        for rule, value in rules.items():
            self.rule(rule.replace("_", "-"), value)

        return self

    # #### `Style.apply`
    # The `apply` method enables style composition, by copying all the rules
    # in one or more input styles into this style.

    # At some point we could implement this in a lazy manner, such that rules
    # are only realyy copied when converting to CSS using the `css` method.
    # However, at the moment I can't see an interesting use case for that functionality,
    # since I seldom modify styles after they are created.
    # Maybe this could be interesting for programmatically-created styles with lots of parameters, or for
    # some kind of interactive application where the user creates a theme.
    # However, in favour of YAGNI, I will refrain from implementing that functionality until
    # proven necessary.

    def apply(self, *others: Style) -> Style:
        """Copy rules from other styles.

        Rules are defined in order, so later styles will override former ones.

        **Parameters**:

        - `others`: A sequence of `Style` instances to copy their rules.
        """
        for other in others:
            for attr, value in other._rules.items():
                self.rule(attr, value)

        return self

    # ### Typographic styles
    # These methods allow manipulating font and text properties.

    # #### `Style.font`
    # Configure font attributes.

    @style_method
    def font(
        self,
        size: Unit = None,
        *,
        weight: FontWeight = None,
        family: str = None,
    ) -> Style:
        if size:
            self.rule("font-size", Unit.infer(size))

        if weight:
            self.rule("font-weight", weight)

        if family:
            self.rule("font-family", family)

    # #### `Style.text`
    # Configure text styling attributes.

    @style_method
    def text(self, *, align: str = None, decoration: str = None) -> Style:
        if align is not None:
            self.rule("text-align", align)
        if decoration is not None:
            if decoration == False:
                decoration = "none"
            self.rule("text-decoration", decoration)

    # #### `Style.center`
    # Shorthand method for center align.

    @style_method
    def center(self) -> Style:
        self.text(align="center")

    # #### `Style.left`
    # Shorthand method for left align.

    @style_method
    def left(self) -> Style:
        self.text(align="left")

    # #### `Style.right`
    # Shorthand method for right align.

    @style_method
    def right(self) -> Style:
        self.text(align="right")

    # #### `Style.justify`
    # Shorthand method for justified align.

    @style_method
    def justify(self) -> Style:
        self.text(align="justify")

    # ### Color styles

    # #### `Style.color`

    @style_method
    def color(self, color: Color) -> Style:
        self.rule("color", color)

    # #### `Style.background`

    @style_method
    def background(self, color: Color) -> Style:
        self.rule("background-color", color)

    @style_method
    def shadow(
        self,
        color: Color = None,
        *,
        x: Unit = 0,
        y: Unit = 0,
        blur: Unit = 0,
        spread: Unit = 0,
    ) -> Style:
        if color is None:
            self.rule("box-shadow", "none")
            return self

        rule = [
            str(Unit.infer(x)),
            str(Unit.infer(y)),
            str(Unit.infer(blur)),
            str(Unit.infer(spread)),
            str(color),
        ]

        self.rule("box-shadow", " ".join(rule))

    # #### `Style.border`

    @style_method
    def border(
        self, width: Unit = None, color: Color = None, *, radius: Unit = None
    ) -> Style:
        if width is not None:
            self.rule("border-width", Unit.infer(width))

        if color is not None:
            self.rule("border-color", color)

        if radius is not None:
            self.rule("border-radius", Unit.infer(radius))

    # ### Visibility styles

    # #### `Style.visibility`

    @style_method
    def visibility(self, visibility: str) -> Style:
        self.rule("visibility", visibility)

    # #### `Style.visible`

    @style_method
    def visible(self) -> Style:
        self.visibility("visible")

    # #### `Style.hidden`

    @style_method
    def hidden(self) -> Style:
        self.visibility("hidden")

    # ### Geometry styles

    # #### `Style.width`

    @style_method
    def width(self, value=None, *, min=None, max=None) -> Style:
        if value is not None:
            self.rule("width", Unit.infer(value, on_float=pc))

        if min is not None:
            self.rule("min-width", Unit.infer(min, on_float=pc))

        if max is not None:
            self.rule("max-width", Unit.infer(max, on_float=pc))

    # #### `Style.height`

    @style_method
    def height(self, value=None, *, min=None, max=None) -> Style:
        if value is not None:
            self.rule("height", Unit.infer(value, on_float=pc))

        if min is not None:
            self.rule("min-height", Unit.infer(min, on_float=pc))

        if max is not None:
            self.rule("max-height", Unit.infer(max, on_float=pc))

    # #### `Style.size`

    @style_method
    def size(self, width: Unit, height: Unit) -> Style:
        self.width(width)
        self.height(height)

    # #### `Style.margin`

    @style_method
    def margin(
        self,
        all=None,
        *,
        left=None,
        right=None,
        top=None,
        bottom=None,
    ) -> Style:
        if all is not None:
            self.rule("margin", Unit.infer(all))
        if left is not None:
            self.rule("margin-left", Unit.infer(left))
        if right is not None:
            self.rule("margin-right", Unit.infer(right))
        if top is not None:
            self.rule("margin-top", Unit.infer(top))
        if bottom is not None:
            self.rule("margin-bottom", Unit.infer(bottom))

    # #### `Style.padding`

    @style_method
    def padding(
        self,
        all=None,
        *,
        left=None,
        right=None,
        top=None,
        bottom=None,
    ) -> Style:
        if all is not None:
            self.rule("padding", Unit.infer(all))
        if left is not None:
            self.rule("padding-left", Unit.infer(left))
        if right is not None:
            self.rule("padding-right", Unit.infer(right))
        if top is not None:
            self.rule("padding-top", Unit.infer(top))
        if bottom is not None:
            self.rule("padding-bottom", Unit.infer(bottom))

    # #### `Style.rounded`

    @style_method
    def rounded(self, radius: Unit = None) -> Style:
        if radius is None:
            radius = 0.25

        self.rule("border-radius", Unit.infer(radius))

    # ### Layout styles

    # #### `Style.display`

    @style_method
    def display(self, display: str) -> Style:
        self.rule("display", display)

    # #### `Style.flexbox`

    @style_method
    def flexbox(
        self,
        direction: str = "row",
        *,
        gap: Unit = 0,
        wrap: bool = False,
        reverse: bool = False,
        align: str = None,
        justify: str = None,
    ) -> Style:
        self.display("flex")

        if reverse:
            direction += "-reverse"

        self.rule("flex-direction", direction)

        if wrap:
            self.rule("flex-wrap", "wrap")

        if align is not None:
            self.rule("align-items", align)

        if justify is not None:
            self.rule("justify-content", justify)

        self.rule("gap", Unit.infer(gap))

    # #### `Style.flex`

    @style_method
    def flex(
        self,
        grow: float = None,
        shrink: float = None,
        basis: int = None,
    ) -> Style:
        if grow is not None:
            self.rule("flex-grow", float(grow))

        if shrink is not None:
            self.rule("flex-shrink", float(shrink))

        if basis is not None:
            self.rule("flex-basis", Unit.infer(basis, on_float=fr))

    # #### `Style.grid`

    @style_method
    def grid(
        self,
        *,
        columns: Union[int, List[GridTemplate]] = None,
        rows: Union[int, List[GridTemplate]] = None,
        auto_columns: GridSize = None,
        auto_rows: GridSize = None,
        gap: Unit = 0,
    ) -> Style:
        self.display("grid")

        if columns is None and rows is None:
            raise ValueError("Either columns or rows must be specified")

        if isinstance(columns, int):
            columns = repeat(columns, fr(1))

        if isinstance(rows, int):
            rows = repeat(rows, fr(1))

        if columns is not None:
            self.rule("grid-template-columns", columns)
        elif auto_columns is not None:
            self.rule("grid-auto-columns", auto_columns)

        if rows is not None:
            self.rule("grid-template-rows", rows)
        elif auto_rows is not None:
            self.rule("grid-auto-rows", auto_rows)

        self.rule("gap", Unit.infer(gap, on_float=fr))

    # #### `Style.columns`

    @style_method
    def columns(
        self,
        count: int,
        min: GridSize = None,
        max: GridSize = None,
        *,
        gap: Unit = 0,
    ) -> Style:
        if min is None:
            min = fr(1)

        if max is None:
            max = fr(1)

        self.grid(columns=repeat(count, minmax(min, max)), gap=gap)

    # #### `Style.rows`

    @style_method
    def rows(
        self,
        count: int,
        min: GridSize = None,
        max: GridSize = None,
        *,
        gap: Unit = 0,
    ) -> Style:
        if min is None:
            min = fr(1)

        if max is None:
            max = fr(1)

        self.grid(rows=repeat(count, minmax(min, max)), gap=gap)

    # #### `Style.place`

    @style_method
    def place(
        self,
        columns: Union[int, Tuple[int, int]] = None,
        rows: Union[int, Tuple[int, int]] = None,
    ) -> Style:
        if columns is not None:
            if isinstance(columns, tuple):
                columns = f"{columns[0]} / {columns[1]+1}"

            self.rule("grid-column", columns)

        if rows is not None:
            if isinstance(rows, tuple):
                rows = f"{rows[0]} / {rows[1]+1}"

            self.rule("grid-row", rows)

    # #### `Style.position`

    @style_method
    def position(
        self,
        position: str,
        *,
        left: int = None,
        right: int = None,
        top: int = None,
        bottom: int = None,
    ) -> Style:
        self.rule("position", position)

        if left is not None:
            self.rule("left", Unit.infer(left))
        if right is not None:
            self.rule("right", Unit.infer(right))
        if top is not None:
            self.rule("top", Unit.infer(top))
        if bottom is not None:
            self.rule("bottom", Unit.infer(bottom))

    # #### `Style.absolute`

    @style_method
    def absolute(
        self,
        *,
        left: int = None,
        right: int = None,
        top: int = None,
        bottom: int = None,
    ) -> Style:
        self.position("absolute", left=left, right=right, top=top, bottom=bottom)

    # #### `Style.relative`

    @style_method
    def relative(
        self,
        *,
        left: int = None,
        right: int = None,
        top: int = None,
        bottom: int = None,
    ) -> Style:
        self.position("relative", left=left, right=right, top=top, bottom=bottom)

    # ### Animations

    # #### `Style.transition`

    @style_method
    def transition(
        self,
        property="all",
        duration: Unit = ms(150),
        timing: str = "linear",
        delay: Unit = ms(0),
    ) -> Style:
        self._transitions.append(
            (
                property,
                Unit.infer(duration, sec, ms),
                timing,
                Unit.infer(delay, sec, ms),
            )
        )

        properties = []
        durations = []
        timings = []
        delays = []

        for property, duration, timing, delay in self._transitions:
            properties.append(property)
            durations.append(str(duration))
            timings.append(timing)
            delays.append(str(delay))

        self.rule("transition-property", ", ".join(properties))
        self.rule("transition-duration", ", ".join(durations))
        self.rule("transition-timing-function", ", ".join(timings))
        self.rule("transition-delay", ", ".join(delays))

    # #### `Style.transform`

    @style_method
    def transform(
        self,
        translate_x: Unit = None,
        translate_y: Unit = None,
        scale_x: float = None,
        scale_y: float = None,
        rotate: Unit = None,
    ) -> Style:
        if translate_x is not None:
            self._transforms["translateX"] = Unit.infer(translate_x)
        if translate_y is not None:
            self._transforms["translateY"] = Unit.infer(translate_y)
        if scale_x is not None:
            self._transforms["scaleX"] = scale_x
        if scale_y is not None:
            self._transforms["scaleY"] = scale_y
        if rotate is not None:
            self._transforms["rotate"] = Unit(rotate, "deg")

        transforms = []

        for transform, value in self._transforms.items():
            transforms.append(f"{transform}({value})")

        self.rule("transform", " ".join(transforms))

    @style_method
    def translate(self, x: Unit = None, y: Unit = None) -> Style:
        self.transform(translate_x=x, translate_y=y)

    @style_method
    def scale(self, scale: float = None, *, x: float = None, y: float = None) -> Style:
        if scale is not None:
            x = scale
            y = scale

        self.transform(scale_x=x, scale_y=y)

    @style_method
    def rotate(self, rotation: float) -> Style:
        self.transform(rotate=rotation)

    # #### `Style.animation`

    @style_method
    def animate(
        self,
        animation: Animation,
        duration: Unit = sec(1),
        iter: int = 1,
        timing: str = "linear",
        direction: str = "normal",
    ) -> Style:
        self._animation_configs.append(
            (animation.name, Unit.infer(duration, sec, ms), timing, iter, direction)
        )

        self._animations.add(animation)

        names = []
        durations = []
        timings = []
        iterations = []
        directions = []

        for name, duration, timing, iter, direction in self._animation_configs:
            names.append(name)
            durations.append(str(duration))
            timings.append(str(timing))
            iterations.append(str(iter))
            directions.append(str(direction))

        self.rule("animation-name", ", ".join(names))
        self.rule("animation-duration", ", ".join(durations))
        self.rule("animation-timing-function", ", ".join(timings))
        self.rule("animation-iteration-count", ", ".join(iterations))
        self.rule("animation-direction", ", ".join(directions))

    # ### Sub-styles

    # #### `Style.on`

    def on(self, state) -> Style:
        selector = self.selector.on(state)
        style = self._children.get(selector.css(), Style(selector))
        self._children[selector.css()] = style
        return style

    # #### `Style.children`

    def children(self, selector: str = "*", *, nth: int = None) -> Style:
        selector = self.selector.children(selector, nth=nth)
        style = self._children.get(selector.css(), Style(selector))
        self._children[selector.css()] = style
        return style

    # ### Rendering methods

    # #### `Style.css`

    def css(self, inline: bool = False) -> str:
        separator = "" if inline else "\n"

        rules = separator.join(
            f"{attr}: {value};" for attr, value in self._rules.items()
        )

        if inline:
            return rules

        selector = self.selector.css() if self.selector is not None else ""
        return f"{selector} {{\n{textwrap.indent(rules, 4*' ')}\n}}"

    # #### `Style.inline`

    def inline(self) -> str:
        return f'style="{self.css(inline=True)}"'

    # #### `Style.markup`

    def markup(self) -> str:
        return self.selector.markup()

    # #### `Style.__str__`

    def __str__(self):
        return self.markup()
