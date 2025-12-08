from violetear import App, Document, StyleSheet, Element, HTML
from violetear.dom import Event

app = App(title="Cached PWA Demo")

# --- 1. Define Styles ---
# We define a stylesheet in Python. We will attach it to the document later.
style = StyleSheet()

style.select("body").rules(
    font_family="sans-serif",
    background="#f4f4f9",
    color="#333",
    display="flex",
    flex_direction="column",
    align_items="center",
    justify_content="center",
    height="100vh",
    margin="0",
)

style.select(".card").rules(
    background="white",
    padding="2rem",
    border_radius="12px",
    box_shadow="0 4px 6px rgba(0,0,0,0.1)",
    text_align="center",
    max_width="400px",
)

style.select("button").rules(
    background="#6200ea",
    color="white",
    border="none",
    padding="10px 20px",
    border_radius="6px",
    font_size="1rem",
    cursor="pointer",
    margin_top="1rem",
    transition="background 0.2s",
)
style.select("button:hover").rules(background="#3700b3")


# --- 2. Define Client Logic ---
# This function runs in the browser (compiled to the client bundle).
@app.client
async def change_color(event: Event):
    from violetear.dom import Document
    import random

    colors = ["#ffebee", "#e3f2fd", "#e8f5e9", "#fff3e0", "#f3e5f5"]
    # We select the element by ID and change its style
    card = Document.find("my-card")
    card.style(background_color=random.choice(colors))

    # Update text
    status = Document.find("status")
    status.text = "Color changed from Python!"


# --- 3. Define Route ---
# pwa=True enables the Service Worker
@app.route("/", pwa=True)
def index():
    doc = Document(title="Cached PWA")

    # Attach the stylesheet.
    # Providing 'href' tells Violetear to serve this as an external CSS file
    # AND cache it in the Service Worker.
    doc.style(sheet=style, href="/static/main.css")

    doc.body.add(
        HTML.div(
            HTML.h1(text="PWA Demo"),
            HTML.p(text="This app works completely offline."),
            HTML.p(text="The CSS and the Python logic below are cached.", id="status"),
            HTML.button(text="Change Card Color").on("click", change_color),
            # div attributes
            id="my-card",
            classes="card",
        )
    )

    return doc


if __name__ == "__main__":
    print("Running Cached PWA at http://0.0.0.0:8000")
    app.run()
