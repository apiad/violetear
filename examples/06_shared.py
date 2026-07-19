"""Tier 6 canonical example — shared state counter across all connected clients.

Demonstrates @app.shared: a reactive dataclass whose fields auto-broadcast
to every connected client. No manual broadcast calls. No request_history.
Open two browser tabs — clicking + in one tab updates the counter in both.

Run:
    python examples/06_shared.py

Then open http://localhost:8000 in two browser tabs.
"""

from dataclasses import dataclass, field

from violetear import App, Document, StyleSheet
from violetear.color import Colors
from violetear.js import DOM, Event
from violetear.units import px, rem

app = App(title="Shared Counter")


@app.shared
@dataclass
class Room:
    count: int = 0
    label: str = "clicks"
    server_version: str = field(default="1.0", metadata={"server_only": True})


sheet = StyleSheet(normalize=True)
sheet.select("body").font(size=rem(1.0), family="system-ui, sans-serif").background(
    Colors.WhiteSmoke
).padding(rem(2))
sheet.select(".card").rules(max_width="360px").margin("auto").background(
    Colors.White
).padding(rem(2)).rounded(px(8)).border(px(1), Colors.Gainsboro)
sheet.select(".count").font(size=rem(4), weight=700).color(Colors.Indigo).rules(
    text_align="center"
)
sheet.select(".btn").rules(
    display="block",
    width="100%",
    padding="12px",
    border="none",
    cursor="pointer",
    font_size="1.25rem",
    font_weight=700,
    margin_top="1rem",
).background(Colors.Indigo).color(Colors.White).rounded(px(6))
sheet.select(".label").font(size=rem(0.875)).color(Colors.SlateGray).rules(
    text_align="center", margin_top="0.25rem"
)


@app.client.callback
async def on_increment(event: Event):
    Room.count = Room.count + 1


@app.view("/")
def index():
    doc = Document(title="Shared Counter")
    doc.style(href="/style.css", sheet=sheet)

    with doc.body as body:
        with body.div(classes="card") as card:
            card.div(classes="count").text(Room.count)
            card.div(classes="label").text(Room.label)
            card.button(text="+1", classes="btn").on("click", on_increment)

    return doc


if __name__ == "__main__":
    app.run()
