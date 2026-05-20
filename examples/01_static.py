"""Tier 1 canonical example — a design-tokens reference page.

Pure markup + CSS, no server. Demonstrates `Document`, `StyleSheet`, the
`Style` fluent builder, the `Colors` named registry, `ElementSet.spawn` for
generated grids, and the `Unit` types (px, rem, em, %).

Run:

    python examples/01_static.py

Then open `01_static.html` in a browser. The script writes that file and
`01_static.css` alongside itself.

Note: violetear's CSS selector parser only supports compound selectors
(tag + classes + id + pseudo) — no descendant combinators. So every
nested element gets its own flat class name (`.swatch-chip` instead of
`.swatch .chip`). This is a real framework limitation worth tracking.
"""

from pathlib import Path

from violetear import Document, HTML, Style, StyleSheet
from violetear.color import Colors, hex
from violetear.units import em, pc, px, rem


# ---------------------------------------------------------------------------
# Token tables
# ---------------------------------------------------------------------------

PALETTE = [
    Colors.Coral,
    Colors.Tomato,
    Colors.Gold,
    Colors.Khaki,
    Colors.OliveDrab,
    Colors.ForestGreen,
    Colors.SeaGreen,
    Colors.Teal,
    Colors.SteelBlue,
    Colors.RoyalBlue,
    Colors.MidnightBlue,
    Colors.Indigo,
    Colors.BlueViolet,
    Colors.MediumOrchid,
    Colors.Crimson,
    Colors.DeepPink,
    Colors.Chocolate,
    Colors.SaddleBrown,
    Colors.Lavender,
    Colors.Silver,
    Colors.DimGray,
    Colors.Black,
]

# Typography demo: rendered as spans with size-variant classes so we don't
# rely on a descendant combinator to style "sample h1" etc.
TYPE_SCALE = [
    ("type-h1", "Aa — Heading 1", "2.5rem · 700"),
    ("type-h2", "Aa — Heading 2", "2.0rem · 700"),
    ("type-h3", "Aa — Heading 3", "1.5rem · 600"),
    ("type-h4", "Aa — Heading 4", "1.25rem · 600"),
    ("type-h5", "Aa — Heading 5", "1.1rem · 600"),
    ("type-h6", "Aa — Heading 6", "1.0rem · 600"),
    (
        "type-body",
        "Body — the quick brown fox jumps over the lazy dog.",
        "1.0rem · 400",
    ),
    ("type-small", "Small — annotations and metadata.", "0.875rem · 400"),
    ("type-caption", "Caption — image labels and footnotes.", "0.75rem · 400"),
]

SPACING_STEPS = [4, 8, 16, 24, 32, 48, 64]

UNITS_DEMO = [
    ("32px (absolute)", px(32)),
    ("2rem  (root-relative)", rem(2.0)),
    ("2em   (parent-relative)", em(2.0)),
    ("25%   (container-relative)", pc(0.25)),
]


# ---------------------------------------------------------------------------
# Stylesheet — flat class selectors only
# ---------------------------------------------------------------------------

sheet = StyleSheet(normalize=True)

sheet.select("body").font(
    size=rem(1.0), family="system-ui, -apple-system, 'Segoe UI', sans-serif"
).color(Colors.DarkSlateGray).background(Colors.WhiteSmoke).padding(rem(2.5))

sheet.select(".page").rules(max_width="960px").margin("auto").background(
    Colors.White
).padding(rem(2.5)).rounded(px(8)).border(px(1), Colors.Gainsboro)

sheet.select(".page-title").font(size=rem(2.5), weight=700).color(Colors.Indigo).margin(
    bottom=rem(0.25)
)

sheet.select(".subtitle").color(Colors.SlateGray).font(size=rem(1.0)).margin(
    bottom=rem(2.0)
)

sheet.select(".tokens-section").margin(top=rem(2.0))

sheet.select(".tokens-heading").font(size=rem(1.5), weight=600).color(
    Colors.DarkSlateGray
).rules(border_bottom=f"2px solid {Colors.Lavender}").padding(bottom=rem(0.25)).margin(
    bottom=rem(1.0)
)

# Palette grid
sheet.select(".palette").rules(
    display="grid",
    grid_template_columns="repeat(auto-fill, minmax(120px, 1fr))",
    gap="16px",
)
sheet.select(".swatch").flexbox(direction="column", gap=px(6))
sheet.select(".swatch-chip").rules(
    height="72px", border="1px solid rgba(0,0,0,0.08)"
).rounded(px(6))
sheet.select(".swatch-name").font(size=rem(0.875), weight=600).color(
    Colors.DarkSlateGray
)
sheet.select(".swatch-hex").font(
    size=rem(0.75), family="ui-monospace, monospace"
).color(Colors.SlateGray)

# Typography rows — each row is sample text + spec
sheet.select(".type-row").flexbox(
    direction="row", gap=px(24), align="baseline"
).padding(top=rem(0.5), bottom=rem(0.5)).rules(
    border_bottom=f"1px solid {Colors.Gainsboro}"
)
sheet.select(".type-sample").rules(flex_grow=1)
sheet.select(".type-rule").font(size=rem(0.8), family="ui-monospace, monospace").color(
    Colors.SlateGray
)
sheet.select(".type-h1").font(size=rem(2.5), weight=700).color(Colors.Indigo)
sheet.select(".type-h2").font(size=rem(2.0), weight=700).color(Colors.Indigo)
sheet.select(".type-h3").font(size=rem(1.5), weight=600).color(Colors.DarkSlateGray)
sheet.select(".type-h4").font(size=rem(1.25), weight=600).color(Colors.DarkSlateGray)
sheet.select(".type-h5").font(size=rem(1.1), weight=600).color(Colors.DarkSlateGray)
sheet.select(".type-h6").font(size=rem(1.0), weight=600).color(Colors.DarkSlateGray)
sheet.select(".type-body").font(size=rem(1.0), weight=400).color(Colors.DarkSlateGray)
sheet.select(".type-small").font(size=rem(0.875), weight=400).color(Colors.SlateGray)
sheet.select(".type-caption").font(size=rem(0.75), weight=400).color(Colors.SlateGray)

# Spacing
sheet.select(".spacing").flexbox(direction="column", gap=px(8))
sheet.select(".spacing-row").flexbox(direction="row", gap=px(12), align="center")
sheet.select(".spacing-bar").rules(height="16px").background(Colors.Coral).rounded(
    px(2)
)
sheet.select(".spacing-label").font(
    size=rem(0.8), family="ui-monospace, monospace"
).color(Colors.SlateGray).rules(min_width="60px")

# Units
sheet.select(".units").flexbox(direction="column", gap=px(8))
sheet.select(".units-row").flexbox(direction="row", gap=px(12), align="center")
sheet.select(".units-bar").rules(height="16px").background(Colors.SteelBlue).rounded(
    px(2)
)
sheet.select(".units-label").font(
    size=rem(0.8), family="ui-monospace, monospace"
).color(Colors.SlateGray).rules(min_width="160px")


# ---------------------------------------------------------------------------
# Document tree
# ---------------------------------------------------------------------------

doc = Document(title="violetear · Design Tokens")
doc.style(href="01_static.css")


def _populate_swatch(color, el):
    """Fill one swatch cell. When spawn() iterates an iterable, the first
    arg is the item itself (here a Color), not an integer index."""
    el.classes("swatch").extend(
        HTML.div(classes="swatch-chip").style(Style().background(color)),
        HTML.div(text=color.name or "—", classes="swatch-name"),
        HTML.div(text=hex(color), classes="swatch-hex"),
    )


with doc.body as body:
    with body.div(classes="page") as page:
        page.h1(text="Design Tokens").classes("page-title")
        page.p(
            text="A reference page for the violetear named-color palette, type scale, spacing, and units."
        ).classes("subtitle")

        # Palette — generated grid via ElementSet.spawn.
        with page.div(classes="tokens-section") as palette_sec:
            palette_sec.h2(text="Palette").classes("tokens-heading")
            palette_grid = palette_sec.div(classes="palette")
            palette_grid.spawn(PALETTE, "div").each(_populate_swatch)

        # Typography — each row uses a size-variant class on the sample span.
        with page.div(classes="tokens-section") as type_sec:
            type_sec.h2(text="Typography").classes("tokens-heading")
            for variant, sample_text, rule in TYPE_SCALE:
                with type_sec.div(classes="type-row") as row:
                    row.div(classes="type-sample").add(
                        HTML.span(text=sample_text).classes(variant)
                    )
                    row.div(text=rule, classes="type-rule")

        # Spacing
        with page.div(classes="tokens-section") as space_sec:
            space_sec.h2(text="Spacing").classes("tokens-heading")
            with space_sec.div(classes="spacing") as box:
                for step in SPACING_STEPS:
                    with box.div(classes="spacing-row") as row:
                        row.div(text=f"{step}px", classes="spacing-label")
                        row.div(classes="spacing-bar").style(Style().width(px(step)))

        # Units
        with page.div(classes="tokens-section") as units_sec:
            units_sec.h2(text="Units").classes("tokens-heading")
            with units_sec.div(classes="units") as box:
                for label, unit in UNITS_DEMO:
                    with box.div(classes="units-row") as row:
                        row.div(text=label, classes="units-label")
                        row.div(classes="units-bar").style(Style().width(unit))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def write_to(out_dir: Path) -> tuple[Path, Path]:
    """Render the document and stylesheet to disk. Returns (html_path, css_path)."""
    html_path = out_dir / "01_static.html"
    css_path = out_dir / "01_static.css"
    doc.render(html_path)
    sheet.render(css_path)
    return html_path, css_path


if __name__ == "__main__":
    html_path, css_path = write_to(Path(__file__).parent)
    print(f"Wrote {html_path}")
    print(f"Wrote {css_path}")
