from violetear import App, Document

app = App(title="Realtime Fire-and-Forget")

# 1. Server-Side Realtime Handler
# Receives the message from the client (no return value sent back)
@app.server.realtime
async def log_on_server(msg: str):
    print(f"🔥 SERVER RECEIVED: {msg}")

# 2. Client-Side Callback
# Must use @app.client.callback to be valid for .on() binding
@app.client.callback
async def on_click_ping(event):
    print("Client: Sending ping to server...")

    # Fire-and-forget call to the server
    await log_on_server("Hello from the Browser!")

# 3. View with Fluent Syntax + Explicit Event Binding
@app.view("/")
def index():
    doc = Document(title="Realtime Test")

    # Use the context manager to get the ElementBuilder 'e'
    with doc.body as e:
        e.h1("Realtime Test")
        e.p("Open your server terminal to see the logs.")

        # Create the button and chain .on() to bind the event
        # This passes the function object 'on_click_ping' directly
        e.button("Send Ping").on("click", on_click_ping)

    return doc

if __name__ == "__main__":
    app.run()