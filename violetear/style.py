from .selector import Selector
from .units import Unit, pc, pt, px, em, rem
from .color import Color
import textwrap


class Style:
    def __init__(self, selector: Selector = None, *, parent: "Style" = None) -> None:
        if isinstance(selector, str):
            selector = Selector.from_css(selector)

        self.selector = selector
        self._rules = {}
        self._parent = parent
        self._children = []

    def rule(self, attr: str, value) -> "Style":
        self._rules[attr] = value
        return self

    def apply(self, *others: "Style") -> "Style":
        for other in others:
            for attr, value in other._rules.items():
                self.rule(attr, value)

        return self

    # Typography

    def font(
        self, size: Unit = None, *, weight: str = None, family: str = None
    ) -> "Style":
        if size:
            self.rule("font-size", Unit.infer(size))

        if weight:
            self.rule("font-weight", weight)

        if family:
            self.rule("font-family", family)

        return self

    def text(self, *, align: str = None) -> "Style":
        if align is not None:
            self.rule("text-align", align)

        return self

    def center(self) -> "Style":
        return self.text(align="center")

    def left(self) -> "Style":
        return self.text(align="left")

    def right(self) -> "Style":
        return self.text(align="right")

    def justify(self) -> "Style":
        return self.text(align="justify")

    # Color

    def color(
        self, color: Color = None, *, rgb=None, hsv=None, hls=None, alpha: float = None
    ) -> "Style":
        if color is None:
            if rgb is not None:
                r, g, b = rgb
                color = Color(r, g, b, alpha)
            elif hsv is not None:
                h, s, v = hsv
                color = Color.from_hsv(h, s, v, alpha)
            elif hls is not None:
                h, l, s = hls
                color = Color.from_hls(h, l, s, alpha)

        return self.rule("color", color)

    def background(
        self, color: Color = None, *, rgb=None, hsv=None, hls=None, alpha: float = None
    ) -> "Style":
        if color is None:
            if rgb is not None:
                r, g, b = rgb
                color = Color(r, g, b, alpha)
            elif hsv is not None:
                h, s, v = hsv
                color = Color.from_hsv(h, s, v, alpha)
            elif hls is not None:
                h, l, s = hls
                color = Color.from_hls(h, l, s, alpha)

        return self.rule("background-color", color)

    # Visibility

    def visibility(self, visibility: str) -> "Style":
        return self.rule("visibilty", visibility)

    def visible(self) -> "Style":
        return self.visibility("visible")

    def hidden(self) -> "Style":
        return self.visibility("hidden")

    # Geometry

    def display(self, display: str) -> "Style":
        self.rule("display", display)
        return self

    def width(self, value=None, *, min=None, max=None):
        if value is not None:
            self.rule("width", Unit.infer(value, on_float=pc))

        if min is not None:
            self.rule("min-width", Unit.infer(min, on_float=pc))

        if max is not None:
            self.rule("max-width", Unit.infer(max, on_float=pc))

        return self

    def height(self, value=None, *, min=None, max=None):
        if value is not None:
            self.rule("height", Unit.infer(value, on_float=pc))

        if min is not None:
            self.rule("min-height", Unit.infer(min, on_float=pc))

        if max is not None:
            self.rule("max-height", Unit.infer(max, on_float=pc))

        return self

    def margin(self, all=None, *, left=None, right=None, top=None, bottom=None):
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

        return self

    def padding(self, all=None, *, left=None, right=None, top=None, bottom=None):
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

        return self

    def rounded(self, radius: Unit = None):
        if radius is None:
            radius = 0.25

        return self.rule("border-radius", Unit.infer(radius))

    # Layout

    def flexbox(
        self,
        direction: str = "row",
        *,
        wrap: bool = False,
        reverse: bool = False,
        align: str = None,
        justify: str = None,
    ) -> "Style":
        self.rule("display", "flex")

        if reverse:
            direction += "-reverse"

        self.rule("flex-direction", direction)

        if wrap:
            self.rule("flex-wrap", "wrap")

        if align is not None:
            self.rule("align-items", align)

        if justify is not None:
            self.rule("justify-content", justify)

        return self

    def flex(
        self,
        grow: float = None,
        shrink: float = None,
        basis: int = None,
    ):
        if grow is not None:
            self.rule("flex-grow", float(grow))

        if shrink is not None:
            self.rule("flex-shrink", float(shrink))

        if basis is not None:
            self.rule("flex-basis", Unit.infer(basis, on_float=pc))

        return self

    def position(
        self,
        position: str,
        *,
        left: int = None,
        right: int = None,
        top: int = None,
        bottom: int = None,
    ) -> "Style":
        self.rule("position", position)

        if left is not None:
            self.rule("left", Unit.infer(left))
        if right is not None:
            self.rule("right", Unit.infer(right))
        if top is not None:
            self.rule("top", Unit.infer(top))
        if bottom is not None:
            self.rule("bottom", Unit.infer(bottom))

        return self

    def absolute(
        self,
        *,
        left: int = None,
        right: int = None,
        top: int = None,
        bottom: int = None,
    ) -> "Style":
        return self.position("absolute", left=left, right=right, top=top, bottom=bottom)

    def relative(
        self,
        *,
        left: int = None,
        right: int = None,
        top: int = None,
        bottom: int = None,
    ) -> "Style":
        return self.position("relative", left=left, right=right, top=top, bottom=bottom)

    # Sub-styles

    def on(self, state) -> "Style":
        style = Style(self.selector.on(state))
        self._children.append(style)
        return style

    def children(self, selector: str = "*", *, nth: int = None) -> "Style":
        style = Style(self.selector.children(selector, nth=nth))
        self._children.append(style)
        return style

    # Rendering methods

    def css(self, inline: bool = False) -> str:
        separator = "" if inline else "\n"

        rules = separator.join(
            f"{attr}: {value};" for attr, value in self._rules.items()
        )

        if inline:
            return rules

        return f"{self.selector.css()} {{\n{textwrap.indent(rules, 4*' ')}\n}}"

    def inline(self) -> str:
        return f'style="{self.css(inline=True)}"'

    def markup(self) -> str:
        return self.selector.markup()

    def __str__(self):
        return self.markup()
