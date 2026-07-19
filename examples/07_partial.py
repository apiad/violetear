"""Tier 7 canonical example — @app.partial + DOM manipulation API.

Demonstrates partial HTML routes: the server returns a raw HTML fragment
that the client fetches and injects into the page via DOM.load(). Reactive
bindings in the fragment are re-hydrated automatically after injection.

Run:
    python examples/07_partial.py

Then open http://localhost:8000 in a browser. Type a message and hit Send;
the message list refreshes via a partial fetch.
"""

from dataclasses import dataclass, field

from violetear import App, Document, StyleSheet
from violetear.markup import HTML
from violetear.color import Colors
from violetear.js import DOM, Event
from violetear.units import px, rem

app = App(title="Partial Chat")


@app.shared
@dataclass
class Room:
    messages: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Partial route — returns an HTML fragment (no Document wrapper)
# ---------------------------------------------------------------------------


@app.partial("/chat/messages")
def render_messages():
    ul = HTML.ul(id="msg-list")
    with ul as b:
        for msg in Room.messages:
            b.li(text=f"{msg['from']}: {msg['text']}")
    return ul


# ---------------------------------------------------------------------------
# Client functions
# ---------------------------------------------------------------------------


@app.client.callback
async def send_msg(event: Event):
    from violetear.js import DOM

    name = DOM.find("name-input").value
    text = DOM.find("msg-input").value
    if not text:
        return
    DOM.find("msg-input").value = ""
    await post_message(name=name, text=text)
    await DOM.query("#msg-area").load("/chat/messages")


# ---------------------------------------------------------------------------
# Server RPC
# ---------------------------------------------------------------------------


@app.server.rpc
async def post_message(name: str, text: str):
    Room.messages.append({"from": name, "text": text})


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

sheet = StyleSheet()

sheet.select("body").font(size=rem(1.0), family="system-ui, sans-serif").rules(
    margin="0"
)
sheet.select(".container").rules(
    max_width="600px", margin="40px auto", padding=str(px(24))
)
sheet.select("input").rules(
    padding=str(px(8)), border="1px solid #ccc", border_radius=str(px(4))
)
sheet.select("button").background(Colors.Indigo).color(Colors.White).rounded(
    px(4)
).rules(padding=f"{px(8)} {px(16)}", border="none", cursor="pointer")

app.style("/style.css", sheet)


@app.view("/")
def index():
    doc = Document(title="Partial Chat")
    doc.head.link_css("/style.css")

    body = doc.body
    c = body.div(classes="container")
    c.h1(text="Partial Chat")

    # Name input
    row = c.div()
    row.label(text="Name: ")
    row.input(id="name-input", type="text", value="Anonymous")

    c.hr()

    # Message area — partial is injected here
    c.div(id="msg-area").ul(id="msg-list")

    c.hr()

    # Send form
    form = c.div()
    form.input(id="msg-input", type="text", placeholder="Type a message…")
    form.button(text="Send").onclick(send_msg)

    return doc


if __name__ == "__main__":
    app.run()
