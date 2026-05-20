"""Tier 5 canonical example — a multi-user chat room with live presence.

WebSocket + Pyodide bundle. Demonstrates the full realtime API:
`@app.server.on("connect")` / `("disconnect")` lifecycle handlers,
`@app.server.realtime` server-side fire-and-forget endpoints,
`@app.client.realtime` server-pushable client functions (both the
`.broadcast(...)` fan-out path and the `.invoke(client_id, ...)` targeted
path for the initial history push), and `@app.client.on("connect")` to
trigger the history request as soon as the WS opens.

Run:

    python examples/05_realtime.py

Then open http://localhost:8000 in two browser tabs. Each tab gets a
random `anon-XXXXXX` name and is shown in the sidebar of the other.
Type a message and hit Send — it appears in both tabs. Change your
display name and the sidebar updates everywhere. Messages and the
user list reset when the server restarts (intentional simplicity —
this example demonstrates the wire protocol, not durable storage).
"""

from violetear import App, Document, StyleSheet
from violetear.color import Colors
from violetear.dom import DOM, Event
from violetear.units import px, rem


app = App(title="Chat Room")


# ---------------------------------------------------------------------------
# Server-side shared state
# ---------------------------------------------------------------------------
#
# In-memory only — every restart wipes the room. A real chat app would
# put this behind a database (see @app.shared once it ships — roadmap
# Phase 4 — for the framework-managed-distribution version).

messages: list[dict] = []  # {from_id, from_name, text}
users: dict[str, str] = {}  # client_id -> display_name


def _system_message(text: str) -> dict:
    return {"from_id": "system", "from_name": "system", "text": text}


# ---------------------------------------------------------------------------
# Server-side: lifecycle handlers + realtime endpoints
# ---------------------------------------------------------------------------


@app.server.on("connect")
async def on_join(client_id: str):
    # Assign a default name. The client's first action after socket-open
    # is to call request_history, which will push the full state back.
    default_name = f"anon-{client_id[:6]}"
    users[client_id] = default_name
    msg = _system_message(f"{default_name} joined")
    messages.append(msg)
    await receive_message.broadcast(msg=msg)
    await set_user_list.broadcast(users=users)


@app.server.on("disconnect")
async def on_leave(client_id: str):
    name = users.pop(client_id, None)
    if name is None:
        return
    msg = _system_message(f"{name} left")
    messages.append(msg)
    await receive_message.broadcast(msg=msg)
    await set_user_list.broadcast(users=users)


@app.server.realtime
async def post_message(client_id: str, text: str):
    text = text.strip()
    if not text:
        return
    name = users.get(client_id, "unknown")
    msg = {"from_id": client_id, "from_name": name, "text": text}
    messages.append(msg)
    await receive_message.broadcast(msg=msg)


@app.server.realtime
async def set_name(client_id: str, new_name: str):
    new_name = new_name.strip()
    if not new_name or client_id not in users:
        return
    users[client_id] = new_name
    await set_user_list.broadcast(users=users)


@app.server.realtime
async def request_history(client_id: str):
    # Targeted invoke — only the requesting client gets the initial state.
    # Different code path from the broadcast above (one connection, not all).
    await receive_history.invoke(client_id, messages=messages, users=users)


# ---------------------------------------------------------------------------
# Client-side: realtime handlers + DOM mutation
# ---------------------------------------------------------------------------


@app.client.realtime
async def receive_message(msg: dict):
    container = DOM.find("chat-log")
    row = DOM.create("div").add("chat-row")
    if msg["from_name"] == "system":
        row.add("chat-row-system")
    name_el = DOM.create("span").add("chat-from")
    name_el.text = msg["from_name"] + ":"
    text_el = DOM.create("span").add("chat-text")
    text_el.text = msg["text"]
    row.append(name_el)
    row.append(text_el)
    container.append(row)


@app.client.realtime
async def set_user_list(users: dict):
    container = DOM.find("user-list")
    container.html("")
    for _client_id, name in users.items():
        row = DOM.create("div").add("user-row")
        row.text = name
        container.append(row)


@app.client.realtime
async def receive_history(messages: list, users: dict):
    # Initial state push from request_history (targeted invoke).
    log = DOM.find("chat-log")
    log.html("")
    for msg in messages:
        row = DOM.create("div").add("chat-row")
        if msg["from_name"] == "system":
            row.add("chat-row-system")
        name_el = DOM.create("span").add("chat-from")
        name_el.text = msg["from_name"] + ":"
        text_el = DOM.create("span").add("chat-text")
        text_el.text = msg["text"]
        row.append(name_el)
        row.append(text_el)
        log.append(row)
    user_container = DOM.find("user-list")
    user_container.html("")
    for _cid, name in users.items():
        row = DOM.create("div").add("user-row")
        row.text = name
        user_container.append(row)


@app.client.on("connect")
async def on_socket_connect():
    # WS is now live — ask the server to push our initial state. The server
    # responds via receive_history.invoke(client_id=...) so only this client
    # gets it (proves the targeted-invoke wire path).
    #
    # `str(get_client_id())` because on second call `get_client_id()` returns
    # a `Thing` proxy (read through session storage) rather than a bare str,
    # and `_call_realtime` json.dumps the kwargs — Thing isn't serializable
    # (see issues/7.8). str() coerces via Thing.__repr__ → the wrapped value.
    from violetear.client import get_client_id

    await request_history(client_id=str(get_client_id()))


@app.client.on("ready")
async def on_ready():
    # Surface the default name in the rename field so the user can edit it.
    from violetear.client import get_client_id

    my_id = str(get_client_id())
    name_input = DOM.find("name-input")
    name_input.value = f"anon-{my_id[:6]}"


@app.client.callback
async def on_send_click(event: Event):
    from violetear.client import get_client_id

    text_el = DOM.find("message-input")
    text = str(text_el.value or "")
    if not text.strip():
        return
    await post_message(client_id=str(get_client_id()), text=text)
    text_el.value = ""


@app.client.callback
async def on_rename_click(event: Event):
    from violetear.client import get_client_id

    name_el = DOM.find("name-input")
    new_name = str(name_el.value or "")
    if not new_name.strip():
        return
    await set_name(client_id=str(get_client_id()), new_name=new_name)


# ---------------------------------------------------------------------------
# Stylesheet — flat class selectors only (gap 7.1)
# ---------------------------------------------------------------------------


sheet = StyleSheet(normalize=True)

sheet.select("body").font(
    size=rem(1.0), family="system-ui, -apple-system, 'Segoe UI', sans-serif"
).color(Colors.DarkSlateGray).background(Colors.WhiteSmoke).padding(rem(1.5))

sheet.select(".page").rules(max_width="900px").margin("auto").background(
    Colors.White
).padding(rem(1.5)).rounded(px(8)).border(px(1), Colors.Gainsboro)

sheet.select(".page-title").font(size=rem(1.5), weight=700).color(Colors.Indigo).margin(
    bottom=rem(1.0)
)

sheet.select(".layout").flexbox(direction="row", gap=px(16)).rules(min_height="420px")

# Sidebar
sheet.select(".sidebar").rules(min_width="180px", flex="0 0 180px").padding(
    rem(0.75)
).background(Colors.WhiteSmoke).rounded(px(6)).border(px(1), Colors.Gainsboro)
sheet.select(".sidebar-heading").font(size=rem(0.875), weight=700).color(
    Colors.SlateGray
).rules(text_transform="uppercase", letter_spacing="0.05em").margin(bottom=rem(0.5))
sheet.select(".user-list").flexbox(direction="column", gap=px(4))
sheet.select(".user-row").font(size=rem(0.875)).color(Colors.DarkSlateGray).rules(
    padding="4px 6px"
).background(Colors.White).rounded(px(4))

# Main column
sheet.select(".main").flexbox(direction="column", gap=px(12)).rules(flex="1")
sheet.select(".chat-log").flexbox(direction="column", gap=px(6)).rules(
    flex="1", overflow_y="auto", padding="8px"
).background(Colors.WhiteSmoke).rounded(px(6)).border(px(1), Colors.Gainsboro)
sheet.select(".chat-row").flexbox(direction="row", gap=px(8), align="baseline").rules(
    padding="4px 6px"
)
sheet.select(".chat-row-system").color(Colors.SlateGray).rules(font_style="italic")
sheet.select(".chat-from").font(size=rem(0.875), weight=700).color(Colors.Indigo)
sheet.select(".chat-text").font(size=rem(0.875)).color(Colors.DarkSlateGray)

# Compose bar
sheet.select(".compose").flexbox(direction="row", gap=px(8))
sheet.select(".compose-input").rules(
    padding="8px 10px",
    border=f"1px solid {Colors.Gainsboro}",
    font_size="1rem",
    flex="1",
).rounded(px(4))
sheet.select(".compose-button").rules(
    padding="8px 14px",
    border="none",
    cursor="pointer",
    font_size="0.875rem",
    font_weight=600,
).background(Colors.Indigo).color(Colors.White).rounded(px(4))

# Rename bar
sheet.select(".rename-row").flexbox(direction="row", gap=px(8), align="center").margin(
    top=rem(0.5)
)
sheet.select(".rename-label").font(size=rem(0.875), weight=600).color(Colors.SlateGray)
sheet.select(".rename-input").rules(
    padding="6px 8px",
    border=f"1px solid {Colors.Gainsboro}",
    font_size="0.875rem",
).rounded(px(4))
sheet.select(".rename-button").rules(
    padding="6px 10px",
    border=f"1px solid {Colors.Gainsboro}",
    cursor="pointer",
    font_size="0.875rem",
    font_weight=600,
).background(Colors.White).color(Colors.DarkSlateGray).rounded(px(4))


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------


@app.view("/")
def index():
    doc = Document(title="Chat Room")
    doc.style(href="/style.css", sheet=sheet)

    with doc.body as body:
        with body.div(classes="page") as page:
            page.h1(text="Chat Room").classes("page-title")

            with page.div(classes="layout") as layout:
                # Sidebar — live user list, filled by receive_history /
                # set_user_list pushes.
                with layout.div(classes="sidebar") as sidebar:
                    sidebar.div(text="Online", classes="sidebar-heading")
                    sidebar.div(classes="user-list").attrs(id="user-list")

                with layout.div(classes="main") as main:
                    # Chat log — filled by receive_message + receive_history.
                    main.div(classes="chat-log").attrs(id="chat-log")

                    # Compose bar.
                    with main.div(classes="compose") as compose:
                        compose.input(classes="compose-input").attrs(
                            id="message-input",
                            type="text",
                            placeholder="Type a message…",
                        )
                        compose.button(text="Send", classes="compose-button").attrs(
                            type="button"
                        ).on("click", on_send_click)

                    # Rename bar.
                    with main.div(classes="rename-row") as rename:
                        rename.span(text="Display name:", classes="rename-label")
                        rename.input(classes="rename-input").attrs(
                            id="name-input", type="text"
                        )
                        rename.button(text="Rename", classes="rename-button").attrs(
                            type="button"
                        ).on("click", on_rename_click)

    return doc


if __name__ == "__main__":
    app.run()
