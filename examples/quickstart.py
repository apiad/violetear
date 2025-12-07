import uvicorn
from violetear import App, StyleSheet
from violetear.markup import Document, Element
from violetear.color import Colors
from violetear.style import Style

# 1. Initialize the App
app = App(title="Violetear Counter")

# --- 1. THE STYLES (Pure Python CSS) ---
style = StyleSheet(
    Style("body")
    .background(Colors.AliceBlue)
    .font(family="sans-serif")
    .flexbox(align="center", justify="center")
    .height("320px")
    .margin(top=20),
    Style(".counter-card")
    .background(Colors.White)
    .padding(40)
    .rounded(15)
    .shadow(blur=20, color="rgba(0,0,0,0.1)")
    .text(align="center"),
    Style(".count-display")
    .font(size=64, weight="bold")
    .color(Colors.SlateBlue)
    .margin(10),
    Style("button")
    .padding("10px 20px")
    .font(size=20, weight="bold")
    .margin(5)
    .rounded(8)
    .border(0)
    .rule("cursor", "pointer")
    .color(Colors.White),
    Style(".btn-plus").background(Colors.MediumSeaGreen),
    Style(".btn-minus").background(Colors.IndianRed),
    Style(".btn:hover").rule("opacity", "0.8"),
)


# --- 2. THE SERVER (FastAPI RPC) ---
@app.server
def report_count(current_count: int, action: str):
    """
    This runs on the server.
    FastAPI automatically validates that current_count is an int.
    """
    print(f"[SERVER] Count is now {current_count} (Action: {action})")
    return {"status": "received"}


# --- 3. THE CLIENT (Pyodide Browser) ---
@app.client
async def handle_change(event):
    """
    Runs in the browser.
    """
    from violetear.dom import Document

    # A. Get current state from DOM
    display = Document.find("display")
    current_value = int(display.text)

    # B. Determine action
    action = event.target.id  # "plus" or "minus"
    new_value = current_value + (1 if action == "plus" else -1)

    # C. Update DOM immediately (Responsive)
    display.text = str(new_value)

    # D. Sync with Server (Background)
    # This calls the @app.server function seamlessly!
    await report_count(current_count=new_value, action=action)


# --- 4. THE UI (Server-Side Rendered) ---
@app.route("/")
def index():
    doc = Document(title="Violetear Counter")
    doc.style(style, href="/style.css")  # Link our style

    doc.body.add(
        Element("div", classes="counter-card").extend(
            Element("h2", text="Isomorphic Counter"),
            # The Count
            Element("div", id="display", classes="count-display", text="0"),
            # Controls - Both call the same Python function
            Element("button", id="minus", text="-", classes="btn-minus btn").on(
                "click", handle_change
            ),
            Element("button", id="plus", text="+", classes="btn-plus btn").on(
                "click", handle_change
            ),
            Element("p", text="Check server console for pings.").style(
                Style().color(Colors.Gray).margin(top=20)
            ),
        )
    )

    return doc


app.run()
