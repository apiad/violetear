from violetear import App, StyleSheet, HTML, Document
from violetear.color import Colors

# 1. Initialize the App
app = App(title="Violetear Demo")

# 2. Define your Styles (The "CSS")
# We define this globally so it's created once
theme = StyleSheet()
theme.select("body").font(family="Helvetica, sans-serif").background(Colors.AliceBlue)
theme.select("h1").color(Colors.Navy).margin(bottom=20)
theme.select(".card").background(Colors.White).padding(20).rounded(10).shadow(
    x=2, y=2, blur=10, color=Colors.Gray
)


# 3. Define your Routes (The "Controller")
@app.route("/")
def index():
    doc = Document(title="My Styled App")

    # Attach the style.
    # The App will detect this, create a route for "/style.css",
    # and render the stylesheet content when the browser asks for it.
    doc.style(theme, href="/style.css")

    # Build the UI (The "View")
    doc.body.extend(
        HTML.h1(text="Welcome to Violetear"),
        HTML.div(classes="card").add(
            HTML.p(text="This is a server-side rendered page.")
        ),
    )

    return doc


# 4. Run the Server
app.run()
