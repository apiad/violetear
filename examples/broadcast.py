import asyncio
from contextlib import asynccontextmanager
from violetear import App, Document, HTML
from violetear.style import Style

# Initialize app
app = App(title="Live Ping", version="v1")


# --- 1. Client Side (Updates the UI) ---
@app.client
async def update_counter(count: int):
    # This runs in the User's Browser
    from violetear.dom import Document

    el = Document.find("counter")
    el.text = f"Server Pings: {count}"
    el.style(color="red" if count % 2 == 0 else "blue")


@app.connect
async def enter(id: str):
    print(f"Client connected {id}")


@app.disconnect
async def exit(id: str):
    print(f"Client disconnected {id}")


# --- 2. Server Side (Background Task) ---
async def background_pinger():
    """Simulates a server event happening every second."""
    count = 0
    while True:
        await asyncio.sleep(1)
        count += 1

        # RPC BROADCAST: Sends 'count' to ALL connected browsers
        await update_counter.broadcast(count)


# --- Lifecycle Management ---
@asynccontextmanager
async def lifespan(api):
    # Startup
    task = asyncio.create_task(background_pinger())
    yield
    # Shutdown (optional cleanup)
    task.cancel()


# Hook into the internal FastAPI router to register lifespan
app.api.router.lifespan_context = lifespan


# --- 3. The UI (HTML) ---
@app.route("/")
def home():
    # 1. Create the Document
    doc = Document(title="Live Counter")

    # 2. Build the Body using HTML helpers
    # We use inline styles here for simplicity, but StyleSheet() is better for real apps

    doc.body.add(
        HTML.div(
            style=Style().height("100vh").flexbox(align="center", justify="center")
        ).add(
            HTML.h1(
                id="counter",
                text="Waiting for server...",
                style=Style().font(size="3rem", family="sans-serif", weight="bold"),
            )
        )
    )

    return doc


if __name__ == "__main__":
    app.run()
