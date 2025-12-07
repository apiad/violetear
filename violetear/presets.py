from __future__ import annotations
from inspect import isgenerator

from typing import Any, Callable, Dict, Iterable, Iterator, List
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
    def define(
        self,
        *,
        variants: Iterable[str] | Iterable[Iterable[str]],
        rule: Callable[[Style, Any]],
        clss: str = "",
        values: Iterable[Any] | Iterable[Iterable[Any]] | None = None,
        name: Callable[..., str] | None = None,
    ):
        _variants = list(variants)

        if isinstance(_variants[0], (list, tuple)) or isgenerator(_variants[0]):
            _variants = list(itertools.product(*_variants))
        else:
            _variants = [[v] for v in _variants]

        if values is None:
            _values = _variants
        else:
            _values = list(values)

            if isinstance(_values[0], (list, tuple)) or isgenerator(_values[0]):
                _values = list(itertools.product(*_values))
            else:
                _values = [[v] for v in _values]

        if name is None:

            def name(*variant):
                return "-".join(map(str, [clss] + list(variant)))

        for variant, value in zip(_variants, _values):
            style = self.select(f".{name(*variant)}")
            rule(style, *value)

        return self


# Atomic CSS

from typing import Dict, List, Optional, Union
from violetear import StyleSheet
from violetear.color import Color, Colors
from violetear.units import Unit, rem, px


class Atomic(UtilitySystem):
    """
    A comprehensive utility-first CSS preset inspired by Tailwind CSS.

    This class generates a wide range of atomic CSS classes based on configurable
    scales for colors, spacing, typography, and more. It acts as a compiler that
    takes a "Theme" configuration and generates the corresponding CSS rules
    using the `UtilitySystem`.

    All parameters are keyword-only arguments to allow for partial overrides
    while keeping the rest of the defaults.

    **Parameters**:

    - `colors`: A dictionary mapping names to `Color` objects.
                Defaults to all standard web colors (e.g., `red`, `blue-500`).
    - `spacing`: A dictionary mapping scale names (e.g., "1", "4") to `Unit` values.
                 Used for padding, margin, width, height, and gap.
    - `screens`: A dictionary mapping breakpoint names (e.g., "md") to pixel widths (`int`).
                 Used to generate responsive variants.
    - `font_sizes`: A dictionary mapping size names (e.g., "xl") to `Unit` values.
    - `font_weights`: A dictionary mapping weight names (e.g., "bold") to integer weights.
    - `border_radius`: A dictionary mapping size names (e.g., "sm") to `Unit` values.
    - `shadows`: A dictionary mapping shadow names to CSS shadow strings.
    - `states`: A list of pseudo-states (e.g., "hover", "focus") to generate
                variants for (e.g., `hover:bg-red`).
    """

    # 1. Colors: Default to all Violetear standard colors
    # We lowercase names to match utility conventions (e.g., "SlateBlue" -> "slateblue")
    DEFAULT_COLORS = {c.name.lower(): c for c in Colors.all()}

    # 2. Spacing Scale: The backbone of sizing and positioning
    DEFAULT_SPACING = {
        "0": px(0),
        "px": px(1),
        "0.5": rem(0.125),
        "1": rem(0.25),
        "1.5": rem(0.375),
        "2": rem(0.5),
        "2.5": rem(0.625),
        "3": rem(0.75),
        "3.5": rem(0.875),
        "4": rem(1),
        "5": rem(1.25),
        "6": rem(1.5),
        "8": rem(2),
        "10": rem(2.5),
        "12": rem(3),
        "16": rem(4),
        "20": rem(5),
        "24": rem(6),
        "32": rem(8),
        "40": rem(10),
        "48": rem(12),
        "56": rem(14),
        "64": rem(16),
        "96": rem(24),
    }

    # 3. Responsive Breakpoints
    DEFAULT_SCREENS = dict(
        sm=640,
        md=768,
        lg=1024,
        xl=1280,
        xxl=1536,
    )

    # 4. Typography
    DEFAULT_FONT_SIZES = dict(
        xs=rem(0.75),
        sm=rem(0.875),
        base=rem(1),
        lg=rem(1.125),
        xl=rem(1.25),
        xxl=rem(1.5),
        xxxl=rem(1.875),
    )

    DEFAULT_FONT_WEIGHTS = dict(
        thin=100,
        light=300,
        normal=400,
        medium=500,
        semibold=600,
        bold=700,
        black=900,
    )

    # 5. Borders & Effects
    DEFAULT_BORDER_RADIUS = dict(
        none=px(0),
        sm=rem(0.125),
        md=rem(0.375),
        lg=rem(0.5),
        xl=rem(0.75),
        full=px(9999),
    )

    DEFAULT_SHADOWS = dict(
        sm="0 1px 2px 0 rgb(0 0 0 / 0.05)",
        md="0 4px 6px -1px rgb(0 0 0 / 0.1)",
        lg="0 10px 15px -3px rgb(0 0 0 / 0.1)",
        xl="0 20px 25px -5px rgb(0 0 0 / 0.1)",
        none="none",
    )

    # 6. State Variants to generate (e.g. hover:...)
    DEFAULT_STATES = ["hover", "focus", "active"]

    def __init__(
        self,
        *,
        colors: dict[str, Color] = DEFAULT_COLORS,
        spacing: dict[str, Unit] = DEFAULT_SPACING,
        screens: dict[str, int] = DEFAULT_SCREENS,
        font_sizes: dict[str, Unit] = DEFAULT_FONT_SIZES,
        font_weights: dict[str, int] = DEFAULT_FONT_WEIGHTS,
        border_radius: dict[str, Unit] = DEFAULT_BORDER_RADIUS,
        shadows: dict[str, str] = DEFAULT_SHADOWS,
        states: list[str] = DEFAULT_STATES,
    ) -> None:
        super().__init__(normalize=True)
        self.colors = colors
        self.spacing = spacing
        self.screens = screens
        self.font_sizes = font_sizes
        self.font_weights = font_weights
        self.border_radius = border_radius
        self.shadows = shadows
        self.states = states

    def _generate(self):
        """
        Orchestrates the generation of all utility rule families.
        """
        # 1. Layout & Flexbox (display, position, flex, grid, etc.)
        self._generate_layout()

        # 2. Spacing (padding, margin, gap)
        self._generate_spacing()

        # 3. Sizing (width, height, min/max)
        self._generate_sizing()

        # 4. Typography (font size, weight, color, alignment)
        self._generate_typography()

        # 5. Backgrounds & Borders (colors, radius, border width)
        self._generate_backgrounds_borders()

        # 6. Effects (shadows, opacity)
        self._generate_effects()

    def _generate_layout(self):
        # Display & Position (No prefix, just the value name)
        # e.g. .block, .flex, .absolute
        self.define(
            variants=[
                "block",
                "inline",
                "flex",
                "grid",
                "hidden",
                "static",
                "fixed",
                "absolute",
                "relative",
            ],
            rule=lambda s, v: s.rule(
                (
                    "display"
                    if v in ["block", "inline", "flex", "grid", "hidden"]
                    else "position"
                ),
                v if v != "hidden" else "none",
            ),
            name=lambda v: v,
        )

        # Flex Direction (row, col...)
        self.define(
            clss="flex",
            variants=["row", "col", "row-reverse", "col-reverse"],
            values=["row", "column", "row-reverse", "column-reverse"],
            rule=lambda s, v: s.flexbox(direction=v),
        )

        # Z-Index
        self.define(
            clss="z",
            variants=["0", "10", "20", "30", "40", "50", "auto"],
            rule=lambda s, v: s.rule("z-index", v),
        )

    def _generate_sizing(self):
        # Width & Height (Spacing Scale)
        # Generates w-1, h-4, etc.
        for prefix, rule_name in [("w", "width"), ("h", "height")]:
            self.define(
                clss=prefix,
                variants=self.spacing.keys(),
                values=self.spacing.values(),
                rule=lambda s, v: s.rule(rule_name, v),
            )

        # Fractions (1/2 -> 50%)
        # We use a custom name lambda to handle the slash (w-1/2 -> .w-1\/2)
        fractions = {"1/2": "50%", "full": "100%", "screen": "100vh"}

        self.define(
            variants=[["w", "h"], fractions.keys()],
            values=[["width", "height"], fractions.values()],
            rule=lambda s, prop, v: s.rule(prop, v),
            name=lambda p, v: f"{p}-{v.replace('/', r'\/')}",
        )

    def _generate_spacing(self):
        # 1. Padding & Margin (Single sides + Axes)
        # Variants: [p, m] x [t, b, l, r, x, y, all] x [Spacing Scale]

        # Helper to map 't' -> 'top', 'x' -> 'left, right', etc.
        def apply_spacing(style, property, side, value):
            kwargs = {}
            if side == "":
                kwargs = {"all": value}
            elif side == "t":
                kwargs = {"top": value}
            elif side == "b":
                kwargs = {"bottom": value}
            elif side == "l":
                kwargs = {"left": value}
            elif side == "r":
                kwargs = {"right": value}
            elif side == "x":
                kwargs = {"left": value, "right": value}
            elif side == "y":
                kwargs = {"top": value, "bottom": value}

            # Call style.padding(...) or style.margin(...)
            getattr(style, property)(**kwargs)

        self.define(
            variants=[
                ["p", "m"],
                ["", "t", "b", "l", "r", "x", "y"],
                self.spacing.keys(),
            ],
            values=[["padding", "margin"], [None] * 7, self.spacing.values()],
            # Logic: property is 'padding'/'margin', side is 't'/'x', value is '1rem'
            rule=lambda s, prop, side, val: apply_spacing(s, prop, side, val),
            name=lambda prop, side, val: f"{prop[0]}{side}-{val}",
        )

        # 2. Gap
        self.define(
            clss="gap",
            variants=self.spacing.keys(),
            values=self.spacing.values(),
            rule=lambda s, v: s.rule("gap", v),
        )

    def _generate_typography(self):
        # Font Sizes (text-sm, text-xl)
        self.define(
            clss="text",
            variants=self.font_sizes.keys(),
            values=self.font_sizes.values(),
            rule=lambda s, v: s.font(size=v),
        )

        # Font Weights (font-bold)
        self.define(
            clss="font",
            variants=self.font_weights.keys(),
            values=self.font_weights.values(),
            rule=lambda s, v: s.font(weight=v),
        )

        # Text Align
        self.define(
            clss="text",
            variants=["left", "center", "right", "justify"],
            rule=lambda s, v: s.text(align=v),
        )

        # Text Colors
        self.define(
            clss="text",
            variants=self.colors.keys(),
            values=self.colors.values(),
            rule=lambda s, v: s.color(v),
        )

    def _generate_backgrounds_borders(self):
        # Background Colors
        self.define(
            clss="bg",
            variants=self.colors.keys(),
            values=self.colors.values(),
            rule=lambda s, v: s.background(v),
        )

        # Border Colors
        self.define(
            clss="border",
            variants=self.colors.keys(),
            values=self.colors.values(),
            rule=lambda s, v: s.border(color=v),
        )

        # Border Radius
        self.define(
            clss="rounded",
            variants=self.border_radius.keys(),
            values=self.border_radius.values(),
            rule=lambda s, v: s.rounded(v),
            name=lambda v: f"rounded-{v}" if v != "default" else "rounded",
        )

    def _generate_effects(self):
        # Shadows
        self.define(
            clss="shadow",
            variants=self.shadows.keys(),
            values=self.shadows.values(),
            rule=lambda s, v: s.rule("box-shadow", v),
        )

        # Default shadow (equivalent to .shadow)
        self.select(".shadow").rule(
            "box-shadow", self.shadows.get("base", "0 1px 3px 0 rgb(0 0 0 / 0.1)")
        )

        # Opacity (0, 25, 50, 75, 100)
        self.define(
            clss="opacity",
            variants=range(0, 101, 25),
            rule=lambda s, v: s.rule("opacity", v / 100),
        )

    def _generate_states(self):
        from violetear import Selector, Style

        # Snapshot current styles to avoid infinite recursion
        base_styles = list(self.styles)

        for style in base_styles:
            # Skip styles that aren't class-based or are already complex
            if not style.selector._classes:
                continue

            original_class = style.selector._classes[0]

            for state in self.states:
                # We create a class name like "hover:bg-red"
                # In CSS this must be escaped as ".hover\:bg-red"
                variant_class = f"{state}\\:{original_class}"

                # Create a new Style manually to handle the escaped class name
                # 1. The selector matches the class (e.g. .hover:bg-red)
                # 2. The .on(state) adds the pseudo-class (e.g. :hover)
                variant_style = Style(Selector(classes=variant_class)).on(state)

                # Copy the rules from the original utility
                variant_style.apply(style)

                # Register it
                self.add(variant_style)
