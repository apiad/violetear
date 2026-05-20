"""Tier 3 canonical example — an interactive length converter.

SSR + client-side Python (Pyodide bundle). Demonstrates `@app.local`
reactive state, `data-bind-value` SSR hydration, `@app.client.callback`
on `oninput`, `@app.client.on("ready")` for boot-time restore,
`@app.server.rpc` with float args + dict return, and
`violetear.storage.store` for cross-reload persistence.

Run:

    python examples/03_interactive.py

Then open http://localhost:8000 in a browser. Edit any of the three
fields (meters / feet / inches) — the other two update live. Toggle to
"precise" mode and the conversion routes through a server RPC for more
decimals. Refresh the page; the last values restore from localStorage.
"""

from dataclasses import dataclass

from violetear import App, Document, StyleSheet
from violetear.color import Colors
from violetear.dom import Event
from violetear.storage import store
from violetear.units import px, rem


app = App(title="Length Converter")


# ---------------------------------------------------------------------------
# Reactive state
# ---------------------------------------------------------------------------


@app.local
@dataclass
class UiState:
    meters: float = 1.0
    feet: float = 3.281
    inches: float = 39.37
    mode: str = "quick"


# Rough client-only constants (quick mode).
QUICK_FT_PER_M = 3.281
QUICK_IN_PER_M = 39.37


# ---------------------------------------------------------------------------
# Server RPC — precise mode
# ---------------------------------------------------------------------------


@app.server.rpc
async def precise_convert(meters: float) -> dict:
    return {
        "feet": meters * 3.28083989501,
        "inches": meters * 39.3700787402,
    }


# ---------------------------------------------------------------------------
# Client-side helpers + callbacks
# ---------------------------------------------------------------------------


@app.client
async def save_state():
    store.last_state = {
        "meters": float(UiState.meters),
        "feet": float(UiState.feet),
        "inches": float(UiState.inches),
        "mode": str(UiState.mode),
    }


@app.client
async def recompute_from_meters(m: float):
    if str(UiState.mode) == "precise":
        result = await precise_convert(meters=m)
        UiState.feet = float(result["feet"])
        UiState.inches = float(result["inches"])
    else:
        UiState.feet = m * QUICK_FT_PER_M
        UiState.inches = m * QUICK_IN_PER_M


@app.client.callback
async def on_meters_change(event: Event):
    try:
        v = float(event.target.value)
    except (ValueError, TypeError):
        return
    UiState.meters = v
    await recompute_from_meters(v)
    await save_state()


@app.client.callback
async def on_feet_change(event: Event):
    try:
        v = float(event.target.value)
    except (ValueError, TypeError):
        return
    UiState.feet = v
    # Anchor on meters so precise/quick paths share one code path.
    if str(UiState.mode) == "precise":
        m = v / 3.28083989501
        result = await precise_convert(meters=m)
        UiState.meters = m
        UiState.inches = float(result["inches"])
    else:
        m = v / QUICK_FT_PER_M
        UiState.meters = m
        UiState.inches = m * QUICK_IN_PER_M
    await save_state()


@app.client.callback
async def on_inches_change(event: Event):
    try:
        v = float(event.target.value)
    except (ValueError, TypeError):
        return
    UiState.inches = v
    if str(UiState.mode) == "precise":
        m = v / 39.3700787402
        result = await precise_convert(meters=m)
        UiState.meters = m
        UiState.feet = float(result["feet"])
    else:
        m = v / QUICK_IN_PER_M
        UiState.meters = m
        UiState.feet = m * QUICK_FT_PER_M
    await save_state()


@app.client.callback
async def on_mode_change(event: Event):
    UiState.mode = str(event.target.value)
    # Re-derive the other two from current meters so the displayed values
    # immediately reflect the precision of the chosen mode.
    await recompute_from_meters(float(UiState.meters))
    await save_state()


@app.client.on("ready")
async def restore():
    saved = store.last_state
    if saved is None:
        return
    # Each lookup on a missing key returns None — skip in that case.
    if saved.meters is not None:
        UiState.meters = float(saved.meters)
    if saved.feet is not None:
        UiState.feet = float(saved.feet)
    if saved.inches is not None:
        UiState.inches = float(saved.inches)
    if saved.mode is not None:
        UiState.mode = str(saved.mode)


# ---------------------------------------------------------------------------
# Stylesheet — flat class selectors only (gap 7.1)
# ---------------------------------------------------------------------------


sheet = StyleSheet(normalize=True)

sheet.select("body").font(
    size=rem(1.0), family="system-ui, -apple-system, 'Segoe UI', sans-serif"
).color(Colors.DarkSlateGray).background(Colors.WhiteSmoke).padding(rem(2.5))

sheet.select(".page").rules(max_width="520px").margin("auto").background(
    Colors.White
).padding(rem(2.5)).rounded(px(8)).border(px(1), Colors.Gainsboro)

sheet.select(".page-title").font(size=rem(2.0), weight=700).color(Colors.Indigo).margin(
    bottom=rem(0.25)
)

sheet.select(".subtitle").color(Colors.SlateGray).font(size=rem(1.0)).margin(
    bottom=rem(2.0)
)

sheet.select(".converter").flexbox(direction="column", gap=px(14))

sheet.select(".field").flexbox(direction="column", gap=px(4))
sheet.select(".field-label").font(size=rem(0.875), weight=600).color(
    Colors.DarkSlateGray
)
sheet.select(".field-input").rules(
    padding="8px 10px",
    border=f"1px solid {Colors.Gainsboro}",
    font_size="1rem",
    font_family="ui-monospace, monospace",
).rounded(px(4))

sheet.select(".mode-row").flexbox(direction="row", gap=px(16), align="center").margin(
    top=rem(1.0)
)
sheet.select(".mode-option").flexbox(direction="row", gap=px(6), align="center").font(
    size=rem(0.9)
).color(Colors.DarkSlateGray)
sheet.select(".mode-input").rules(cursor="pointer")

sheet.select(".footer").margin(top=rem(1.5)).color(Colors.SlateGray).font(
    size=rem(0.8), family="ui-monospace, monospace"
)
sheet.select(".footer-mode").font(weight=700).color(Colors.Indigo)


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------


@app.view("/")
def index():
    doc = Document(title="Length Converter")
    doc.style(href="/style.css", sheet=sheet)

    with doc.body as body:
        with body.div(classes="page") as page:
            page.h1(text="Length Converter").classes("page-title")
            page.p(
                text="Edit any field — the other two update live. Switch modes for precision."
            ).classes("subtitle")

            with page.div(classes="converter") as form:
                # Meters
                with form.div(classes="field") as field:
                    with field.label(text="Meters", classes="field-label") as lbl:
                        lbl.input(classes="field-input").attrs(
                            type="number", step="0.01"
                        ).value(UiState.meters).on("input", on_meters_change)

                # Feet
                with form.div(classes="field") as field:
                    with field.label(text="Feet", classes="field-label") as lbl:
                        lbl.input(classes="field-input").attrs(
                            type="number", step="0.01"
                        ).value(UiState.feet).on("input", on_feet_change)

                # Inches
                with form.div(classes="field") as field:
                    with field.label(text="Inches", classes="field-label") as lbl:
                        lbl.input(classes="field-input").attrs(
                            type="number", step="0.01"
                        ).value(UiState.inches).on("input", on_inches_change)

                # Mode toggle — two radios sharing name="mode".
                with form.div(classes="mode-row") as modes:
                    with modes.label(text="quick", classes="mode-option") as lbl:
                        lbl.input(classes="mode-input").attrs(
                            type="radio",
                            name="mode",
                            value="quick",
                            checked="checked",
                        ).on("change", on_mode_change)
                    with modes.label(text="precise", classes="mode-option") as lbl:
                        lbl.input(classes="mode-input").attrs(
                            type="radio", name="mode", value="precise"
                        ).on("change", on_mode_change)

            with page.div(classes="footer") as footer:
                footer.span(text="mode: ")
                footer.span(classes="footer-mode").text(UiState.mode)

    return doc


if __name__ == "__main__":
    app.run()
