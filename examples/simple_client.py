from violetear import App
from violetear.markup import Document, Element

# 1. Initialize the App
app = App(title="Interactive Python Demo")


# 2. Define Client-Side Code
# This function is compiled into the bundle and sent to the browser.
@app.client
def on_button_click(event):
    # This print shows up in the Browser DevTools Console!
    print("Hello from Client-Side Python!")

    # You can even use the Pyodide/JS bridge
    from js import alert

    alert("It works! Python is running in your browser.")


# 3. Define Server-Side Route
@app.route("/")
def home():
    doc = Document(title="Client-Side Demo")

    # 4. Build the UI
    # We create a button and attach the Python function directly.
    btn = Element("button", text="Click Me!").on(
        "click", on_button_click
    )  # <--- The Magic Link

    doc.body.extend(
        Element("h1", text="Violetear Full-Stack Demo"),
        Element("p", text="Open your browser console (F12) and click the button."),
        btn,
    )

    return doc


app.run()
