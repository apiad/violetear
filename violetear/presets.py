from __future__ import annotations
from inspect import isgenerator

from typing import Any, Callable, Dict, List
import itertools
from violetear.color import Color, Colors
from violetear.style import Style
from violetear.stylesheet import StyleSheet
from violetear.units import Unit

# ## Flex-based grid system


class FlexGrid(StyleSheet):
    def __init__(
        self,
        columns: int = 12,
        breakpoints=None,
        row_class="row",
        base_class="span",
    ) -> None:
        super().__init__()

        self._columns = columns
        self._row_class = row_class
        self._base_class = base_class

        self.select(f".{row_class}").flexbox(wrap=True)

        self._make_grid_styles(columns)

        if breakpoints is None:
            return

        for cls, (size, cols) in breakpoints.items():
            with self.media(max_width=size):
                self._make_grid_styles(cols, cls)

    def _make_grid_styles(self, columns, custom=None):
        for size in range(1, columns):
            self.select(f".span-{size}").width(size / columns)

        for size in range(columns, 13):
            self.select(f".span-{size}").width(1.0)

        if custom:
            for size in range(1, columns + 1):
                self.select(f".{custom}-{size}").width(size / columns)


# ## Semantic input system


class SemanticDesign(StyleSheet):
    def __init__(
        self,
        *,
        text_class: str = "text",
        button_class: str = "button",
        sizes: Dict[str, Unit] = dict(
            small=1.0,
            medium=1.4,
            large=2,
        ),
        colors: Dict[str, Color] = dict(
            normal=Colors.White.lit(0.9),
            primary=Colors.Blue.lit(0.3),
            success=Colors.Green.lit(0.3),
            warning=Colors.Orange.lit(0.6),
            error=Colors.Red.lit(0.3),
        ),
    ) -> None:
        super().__init__()

        self._text_class = text_class
        self._button_class = button_class
        self._sizes = sizes
        self._colors = colors

    def typography(self) -> SemanticDesign:
        text_style = self.select(f".{self._text_class}").color(Colors.Black.lit(0.2))

        for cls, font in self._sizes.items():
            self.select(f".{self._text_class}.{cls}").font(size=font)

        for cls, color in self._colors.items():
            self.select(f".{self._text_class}.{cls}").color(color.lit(0.2))

        return self

    def buttons(self) -> SemanticDesign:
        btn_style = (
            self.select(f".{self._button_class}")
            .rule("cursor", "pointer")
            .rounded()
            .shadow(Colors.Black.transparent(0.2), x=2, y=2, blur=4)
            .transition(duration=50)
        )

        for cls, font in self._sizes.items():
            pd = font / 4
            btn_size = (
                self.select(f".{self._button_class}.{cls}")
                .font(size=font)
                .padding(left=pd * 2, top=pd, bottom=pd, right=pd * 2)
            )

        for cls, color in self._colors.items():
            if color.lightness < 0.4:
                text_color = color.lit(0.9)
                accent_color = Colors.White
            else:
                text_color = color.lit(0.1)
                accent_color = Colors.Black

            btn_style = self.select(f".btn.{cls}").background(color).color(text_color)
            hover_style = (
                btn_style.on("hover").background(color.lighter(0.2)).color(accent_color)
            )
            active_style = (
                btn_style.on("active")
                .background(color.darker(0.1))
                .color(accent_color)
                .shadow(color.lit(0.2).transparent(0.2), x=0, y=0, blur=2, spread=1)
            )

        return self

    def all(self) -> SemanticDesign:
        self.typography()
        self.buttons()

        return self


# ## Utility system


class UtilitySystem(StyleSheet):
    def __init__(self) -> None:
        super().__init__()

    def define(
        self,
        *,
        variants: List[str],
        rule: Callable[[Style, Any]],
        clss: str = "",
        values: List[Any] = None,
        name: Callable = None,
    ):
        variants = list(variants)

        if isinstance(variants[0], (list, tuple)) or isgenerator(variants[0]):
            variants = list(itertools.product(*variants))
        else:
            variants = [[v] for v in variants]

        if values is None:
            values = variants
        else:
            values = list(values)

            if isinstance(values[0], (list, tuple)) or isgenerator(values[0]):
                values = list(itertools.product(*values))
            else:
                values = [[v] for v in values]

        if name is None:

            def name(*variant):
                return "-".join(map(str, [clss] + list(variant)))

        for variant, value in zip(variants, values):
            style = self.select(f".{name(*variant)}")
            rule(style, *value)

        return self
