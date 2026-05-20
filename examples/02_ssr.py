"""Tier 2 canonical example — a server-rendered guestbook.

SSR-only, no client-side Python. Demonstrates `App`, `@app.view` for GET
routes, raw `@app.api.post` with FastAPI's `Form(...)` for form-driven
mutation, `doc.style(href=..., sheet=...)` for auto-served CSS, and the
`with element as builder:` markup pattern.

Run:

    python examples/02_ssr.py

Then open http://localhost:8000 in a browser. Submit the form and the new
entry shows up on reload (303 redirect back to `/`). The store is in-memory
and resets on restart — intentional simplicity.
"""

from datetime import datetime

from fastapi import Form
from fastapi.responses import RedirectResponse

from violetear import App, Document, HTML, StyleSheet
from violetear.color import Colors
from violetear.units import px, rem


app = App(title="Guestbook")

# In-memory store. Each entry is {name, message, timestamp}. Resets on restart.
entries: list[dict] = []


# ---------------------------------------------------------------------------
# Stylesheet — flat class selectors only (no descendant combinators yet)
# ---------------------------------------------------------------------------

sheet = StyleSheet(normalize=True)

sheet.select("body").font(
    size=rem(1.0), family="system-ui, -apple-system, 'Segoe UI', sans-serif"
).color(Colors.DarkSlateGray).background(Colors.WhiteSmoke).padding(rem(2.5))

sheet.select(".page").rules(max_width="640px").margin("auto").background(
    Colors.White
).padding(rem(2.5)).rounded(px(8)).border(px(1), Colors.Gainsboro)

sheet.select(".page-title").font(size=rem(2.0), weight=700).color(Colors.Indigo).margin(
    bottom=rem(0.25)
)

sheet.select(".subtitle").color(Colors.SlateGray).font(size=rem(1.0)).margin(
    bottom=rem(2.0)
)

sheet.select(".section-heading").font(size=rem(1.25), weight=600).color(
    Colors.DarkSlateGray
).margin(top=rem(2.0), bottom=rem(1.0))

# Form
sheet.select(".guestbook-form").flexbox(direction="column", gap=px(12))
sheet.select(".form-field").flexbox(direction="column", gap=px(4))
sheet.select(".form-label").font(size=rem(0.875), weight=600).color(
    Colors.DarkSlateGray
)
sheet.select(".form-input").rules(
    padding="8px 10px", border=f"1px solid {Colors.Gainsboro}", font_size="1rem"
).rounded(px(4))
sheet.select(".form-textarea").rules(
    padding="8px 10px",
    border=f"1px solid {Colors.Gainsboro}",
    font_size="1rem",
    min_height="80px",
    font_family="inherit",
).rounded(px(4))
sheet.select(".form-submit").rules(
    padding="10px 16px",
    border="none",
    cursor="pointer",
    font_size="1rem",
    font_weight=600,
).background(Colors.Indigo).color(Colors.White).rounded(px(4))

# Entries
sheet.select(".entries").flexbox(direction="column", gap=px(12))
sheet.select(".entries-empty").color(Colors.SlateGray).font(size=rem(0.875)).rules(
    font_style="italic"
)
sheet.select(".entry").padding(rem(1.0)).background(Colors.WhiteSmoke).rounded(
    px(6)
).border(px(1), Colors.Gainsboro)
sheet.select(".entry-header").flexbox(
    direction="row", gap=px(12), align="baseline"
).margin(bottom=rem(0.5))
sheet.select(".entry-name").font(weight=700).color(Colors.Indigo)
sheet.select(".entry-time").font(
    size=rem(0.75), family="ui-monospace, monospace"
).color(Colors.SlateGray)
sheet.select(".entry-message").color(Colors.DarkSlateGray).rules(
    white_space="pre-wrap", line_height=1.5
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.view("/")
def index():
    doc = Document(title="Guestbook")
    doc.style(href="/style.css", sheet=sheet)

    with doc.body as body:
        with body.div(classes="page") as page:
            page.h1(text="Guestbook").classes("page-title")
            page.p(
                text="Leave a note. It will stay until the server restarts."
            ).classes("subtitle")

            # New-entry form — POSTs to /entries (handled by FastAPI below).
            # We use the nested-label pattern (<label>Text<input/></label>) instead
            # of for=/id= pairing — violetear's .attrs() renders kwargs literally, so
            # `for_=` leaks as `for_="..."` in the HTML (see gap 7.4).
            page.h2(text="Sign the book").classes("section-heading")
            with page.form(classes="guestbook-form").attrs(
                method="post", action="/entries"
            ) as form:
                with form.div(classes="form-field") as field:
                    with field.label(text="Name", classes="form-label") as lbl:
                        lbl.input(classes="form-input").attrs(
                            type="text", name="name", required="required"
                        )
                with form.div(classes="form-field") as field:
                    with field.label(text="Message", classes="form-label") as lbl:
                        lbl.textarea(classes="form-textarea").attrs(
                            name="message", required="required"
                        )
                form.button(text="Add entry", classes="form-submit").attrs(
                    type="submit"
                )

            # Existing entries — newest first.
            page.h2(text="Entries").classes("section-heading")
            with page.div(classes="entries") as entry_list:
                if not entries:
                    entry_list.div(
                        text="No entries yet — be the first.",
                        classes="entries-empty",
                    )
                else:
                    for entry in reversed(entries):
                        with entry_list.div(classes="entry") as card:
                            with card.div(classes="entry-header") as header:
                                header.span(text=entry["name"], classes="entry-name")
                                header.span(
                                    text=entry["timestamp"], classes="entry-time"
                                )
                            card.div(text=entry["message"], classes="entry-message")

    return doc


@app.api.post("/entries")
async def add_entry(name: str = Form(...), message: str = Form(...)):
    entries.append(
        {
            "name": name.strip(),
            "message": message.strip(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
    )
    return RedirectResponse(url="/", status_code=303)


if __name__ == "__main__":
    app.run()
