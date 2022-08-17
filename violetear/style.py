from .selector import Selector
from .units import Unit, pc, pt, px
from .color import Color
import textwrap


class Style:
    def __init__(self, selector: Selector = None) -> None:
        self.selector = selector
        self._rules = {}

    def rule(self, attr: str, value) -> "Style":
        self._rules[attr] = value
        return self

    def font(self, size: Unit = None, *, weight: str = None) -> "Style":
        if size:
            if not isinstance(size, Unit):
                size = pt(size)

            self.rule("font-size", size)

        if weight:
            self.rule("font-weight", weight)

        return self

    def color(
        self, color: Color = None, *, rgb=None, hsv=None, alpha: float = None
    ) -> "Style":
        if color is None:
            if rgb is not None:
                r, g, b = rgb
                color = Color(r, g, b, alpha)
            if hsv is not None:
                h, s, v = hsv
                color = Color.from_hsv(h, s, v, alpha)

        return self.rule("color", color)

    def background(
        self, color: Color, *, rgb=None, hsv=None, alpha: float = None
    ) -> "Style":
        if color is None:
            if rgb is not None:
                r, g, b = rgb
                color = Color(r, g, b, alpha)
            if hsv is not None:
                h, s, v = hsv
                color = Color.from_hsv(h, s, v, alpha)

        return self.rule("background", color)

    def display(self, display: str) -> "Style":
        self.rule("display", display)
        return self

    def apply(self, *others: "Style") -> "Style":
        for other in others:
            for attr, value in other._rules.items():
                self.rule(attr, value)

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

    def width(self, value):
        return self.rule("width", Unit.infer(value))

    def height(self, value):
        return self.rule("height", Unit.infer(value))

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
