from dataclasses import dataclass, field
from violetear.app import App
from violetear.markup import Document
from violetear import StyleSheet, Style
from violetear.dom import Event

# --- 1. Instantiate the App ---
app = App(title="Reactive Engine Demo")

# --- 2. Define the Reactive State ---
@app.local
@dataclass
class UiState:
    count: int = 0
    username: str = "Guest"
    theme: str = "light"

# --- 3. Define Client-Side Logic ---
@app.client.callback
async def increment(event: Event):
    UiState.count += 1

@app.client.callback
async def toggle_theme(event: Event):
    if UiState.theme == "light":
        UiState.theme = "dark"
    else:
        UiState.theme = "light"

@app.client.callback
async def update_name(event: Event):
    UiState.username = event.target.value

@app.client.callback
async def reset_all(event: Event):
    UiState.count = 0
    UiState.username = "Guest"
    UiState.theme = "light"

# --- 4. Define the View ---
@app.view("/")
def home():
    doc = Document(title="Reactive Demo")

    # --- Define Styles using the Violetear StyleSheet API ---
    sheet = StyleSheet()

    # Define Theme Variables
    # We use .rule() explicitly for CSS variables since python kwargs don't support dashes
    sheet.select(".light").rule("--bg", "#ffffff").rule("--fg", "#333333")
    sheet.select(".dark").rule("--bg", "#333333").rule("--fg", "#ffffff")

    # Define Global Body Styles
    sheet.select("body").font(family="sans-serif").margin(0).padding(0)

    # Attach the stylesheet to the document head
    doc.style(sheet=sheet, inline=True)

    # --- Build the UI ---
    with doc.body as b:

        # Container with inline styles using the Style() fluent API
        container_style = (
            Style()
            .padding("20px")
            .rule("transition", "all 0.3s ease")
            .background("var(--bg)")
            .color("var(--fg)")
            .height(min="100vh")
        )

        # We chain .style() BEFORE the context manager
        with b.div(class_name=UiState.theme, id="app-container").style(container_style) as container:

            container.h1("Reactive Engine Demo")

            # Card Style
            card_style = (
                Style()
                .border(width="1px", color="#ccc")
                .padding("20px")
                .rounded("8px")
            )

            with container.div().style(card_style) as card:
                # Text Binding
                card.p().text("Current Count: ").add(
                    card.span()
                        .text(UiState.count)
                        .style(Style().font(weight="bold", size="20px"))
                )

                card.button("Increment").on("click", increment).style(
                    Style().padding("8px 16px").rule("cursor", "pointer")
                )

            # Input Section
            with container.div().style(Style().margin(top="20px")) as form:
                form.label("Enter your name: ")

                # Value Binding
                form.input(type="text").on("input", update_name).value(UiState.username).style(
                    Style().padding("8px").margin(left="10px")
                )

                form.p("Hello, ").add(
                    form.span()
                        .text(UiState.username)
                        .style(Style().font(weight="bold"))
                )

            # Controls Section
            with container.div().style(Style().margin(top="20px")) as controls:
                btn_style = Style().padding("8px 16px").rule("cursor", "pointer")

                controls.button("Toggle Theme").on("click", toggle_theme).style(btn_style)

                controls.button("Reset").on("click", reset_all).style(
                    # Extend the base button style with margin
                    Style().apply(btn_style).margin(left="10px")
                )

    return doc

if __name__ == "__main__":
    app.run(port=8000)