import asyncio
import json
import uuid

from violetear.storage import session

# Pyiodide-specific imports that don't work in the IDE
from js import document, window, WebSocket, console  # type: ignore
from pyodide.ffi import create_proxy  # type: ignore


def get_client_id():
    client_id = session.get("VIOLETEAR_ID")

    if client_id is None:
        client_id = str(uuid.uuid4())

    session["VIOLETEAR_ID"] = client_id
    return client_id


def get_socket_url():
    """Calculates the correct WebSocket URL based on the current page."""
    protocol = "wss" if window.location.protocol == "https:" else "ws"
    host = window.location.host
    client_id = get_client_id()
    return f"{protocol}://{host}/_violetear/ws?client_id={client_id}"


def setup_socket_listener(scope):
    """
    Establishes a WebSocket connection to the server for RPC.
    """
    url = get_socket_url()
    socket = WebSocket.new(url)

    print("Setting up sockets")

    def on_open(event):
        console.log(f"[Violetear] ✅ Connected to Live RPC at {url}")

    def on_message(event):
        """
        Handles incoming RPC commands from the server.
        """
        try:
            # event.data is a string coming from the server
            data = json.loads(event.data)

            if data.get("type") == "rpc":
                func_name = data["func"]
                args = data.get("args", [])
                kwargs = data.get("kwargs", {})

                # 1. Find the function in the client's global scope
                if func_name in scope:
                    func = scope[func_name]

                    # 2. Schedule the execution
                    # Use asyncio to ensure it runs properly in the Pyodide loop
                    asyncio.create_task(func(*args, **kwargs))
                else:
                    console.warn(
                        f"[Violetear] ⚠️ RPC Warning: Function '{func_name}' not found in client scope."
                    )

        except Exception as e:
            console.error(f"[Violetear] ❌ RPC Error: {str(e)}")

    def on_close(event):
        console.log("[Violetear] 🔌 Connection lost. Reconnecting in 3s...")
        # Use create_proxy for the timeout callback too
        retry = create_proxy(lambda: setup_socket_listener(scope))
        window.setTimeout(retry, 3000)

    # Use create_proxy to ensure these python functions aren't garbage collected
    # while the JS side still needs them.
    socket.onopen = create_proxy(on_open)
    socket.onmessage = create_proxy(on_message)
    socket.onclose = create_proxy(on_close)

    # Keep reference to socket on window to prevent it from being GC'd
    window.violetear_socket = socket


def hydrate(scope):
    """
    Scans the DOM for [data-on-event] attributes and binds them to Python functions.
    """

    def create_handler(func_name):
        async def handler(event):
            if func_name in scope:
                await scope[func_name](event)
            else:
                console.error(f"Handler '{func_name}' not found")

        return handler

    elements = document.querySelectorAll("*")

    for i in range(elements.length):
        el = elements.item(i)
        for attr in el.attributes:
            name = attr.name
            if name.startswith("data-on-"):
                event_name = name.replace("data-on-", "")
                func_name = attr.value

                # Bind the event using create_proxy
                handler = create_handler(func_name)
                proxy = create_proxy(handler)

                # Store proxy on element to prevent GC (optional but good practice)
                if not hasattr(el, "_py_listeners"):
                    el._py_listeners = []
                el._py_listeners.append(proxy)

                el.addEventListener(event_name, proxy)

    setup_socket_listener(scope)
