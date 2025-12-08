import uvicorn
from violetear import App, StyleSheet
from violetear.markup import Document, HTML
from violetear.color import Colors
from violetear.style import Style
from violetear.dom import Event

# 1. Initialize the App
app = App(title="Violetear Counter")

# --- 1. THE STYLES (Pure Python CSS) ---
style = StyleSheet()

style.select("body").background(Colors.AliceBlue).font(family="sans-serif").flexbox(
    align="center", justify="center"
).height("320px").margin(top=20)
style.select(".counter-card").background(Colors.White).padding(40).rounded(15).shadow(
    blur=20, color="rgba(0,0,0,0.1)"
).text(align="center")
style.select(".count-display").font(size=64, weight="bold").color(
    Colors.SlateBlue
).margin(10)
style.select("button").padding("10px 20px").font(size=20, weight="bold").margin(
    5
).rounded(8).border(0).rule("cursor", "pointer").color(Colors.White)
style.select(".btn-plus").background(Colors.MediumSeaGreen)
style.select(".btn-minus").background(Colors.IndianRed)
style.select(".btn:hover").rule("opacity", "0.8")


# --- 2. THE SERVER (FastAPI RPC) ---
@app.server
async def report_count(current_count: int, action: str):
    """
    This runs on the server.
    FastAPI automatically validates that current_count is an int.
    """
    print(f"[SERVER] Count is now {current_count} (Action: {action})")
    return {"status": "received"}


# --- 3. THE CLIENT (Pyodide Browser) ---


@app.client
async def handle_change(event: Event):
    """
    Runs in the browser.
    """
    from violetear.dom import Document
    from violetear.storage import store

    # A. Get current state from DOM
    display = Document.find("display")
    current_value = int(display.text)

    # B. Determine action
    action = event.target.id  # "plus" or "minus"
    new_value = current_value + (1 if action == "plus" else -1)

    # C. Update DOM immediately (Responsive)
    display.text = str(new_value)

    # D. Store in LocalStorage
    store.count = new_value

    # E. Sync with Server (Background)
    # This calls the @app.server function seamlessly!
    await report_count(current_count=new_value, action=action)


@app.startup
async def init_counter():
    """
    Runs automatically when the page loads (Client-Side).
    Restores the counter from Local Storage.
    """
    from violetear.dom import Document
    from violetear.storage import store

    # Check if we have a saved count
    saved_count = store.count

    if saved_count is not None:
        Document.find("display").text = str(saved_count)
        print(f"Restored count: {saved_count}")


# --- 4. THE UI (Server-Side Rendered) ---


@app.route("/")
def index():
    doc = Document(title="Violetear Counter")
    doc.style(style, href="/style.css")  # Link our style

    doc.body.add(
        HTML.div(classes="counter-card").extend(
            HTML.h2(text="Isomorphic Counter"),
            # The Count
            HTML.div(id="display", classes="count-display", text="0"),
            # Controls - Both call the same Python function
            HTML.button(id="minus", text="-", classes="btn-minus btn").on(
                "click", handle_change
            ),
            HTML.button(id="plus", text="+", classes="btn-plus btn").on(
                "click", handle_change
            ),
            HTML.p(text="Check server console for pings.").style(
                Style().color(Colors.Gray).margin(top=20)
            ),
        )
    )

    return doc


app.run()
