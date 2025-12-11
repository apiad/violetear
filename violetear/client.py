import asyncio
import json
import uuid

from violetear.storage import session

# We use a try/except block for these imports so this file
# doesn't crash if imported in a non-browser environment (like for testing).
try:
    from js import document, window, WebSocket, console, Object # type: ignore
    from pyodide.ffi import create_proxy, to_js # type: ignore
except ImportError:
    pass


# --- THE REACTIVE REGISTRY ---
class ReactiveRegistry:
    """
    The central Pub/Sub engine for the client.
    Maps 'State Paths' (e.g. 'Ui.theme') to 'Subscriber Callbacks'.
    """

    # storage: { "path": { "subscription_id": callback_function } }
    _subscribers = {}
    _sub_counter = 0

    @staticmethod
    def bind(path: str, callback):
        """
        Subscribes a callback function to a specific state path.
        Returns an 'unsubscribe' function that the caller must use to clean up.
        """
        if path not in ReactiveRegistry._subscribers:
            ReactiveRegistry._subscribers[path] = {}

        # Generate a unique ID for this subscription
        sub_id = ReactiveRegistry._sub_counter
        ReactiveRegistry._sub_counter += 1

        # Store the callback
        ReactiveRegistry._subscribers[path][sub_id] = callback

        # Return the cleanup closure
        def unsubscribe():
            if path in ReactiveRegistry._subscribers:
                # Remove this specific subscription
                ReactiveRegistry._subscribers[path].pop(sub_id, None)

                # Clean up empty keys to save memory
                if not ReactiveRegistry._subscribers[path]:
                    del ReactiveRegistry._subscribers[path]

        return unsubscribe

    @staticmethod
    def notify(path: str, new_value):
        """
        Called by ReactiveProxy (from state.py) when a value changes.
        Triggers all registered callbacks for that path.
        """
        if path in ReactiveRegistry._subscribers:
            # Iterate over a copy of values in case a callback modifies the list
            for callback in list(ReactiveRegistry._subscribers[path].values()):
                try:
                    # We pass the raw value to the callback
                    callback(new_value)
                except Exception as e:
                    print(f"[Violetear] Error in reactive update for '{path}': {str(e)}")


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
        print(f"[Violetear] ✅ Connected to Live RPC at {url}")

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
            print(f"[Violetear] ❌ RPC Error: {str(e)}")

    def on_close(event):
        print("[Violetear] 🔌 Connection lost. Reconnecting in 3s...")
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
                print(f"Handler '{func_name}' not found")

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


async def _call_rpc(func_name, arg_names, args, kwargs):
    """
    Helper to perform an HTTP RPC call to the server.
    Maps positional arguments to their names to satisfy Pydantic models.
    """
    from pyodide.http import pyfetch

    # Map positional args to names
    payload = {k: v for k, v in zip(arg_names, args)}
    payload.update(kwargs)

    response = await pyfetch(
        f"/_violetear/rpc/{func_name}",
        method="POST",
        headers={"Content-Type": "application/json"},
        body=json.dumps(payload),
    )

    if not response.ok:
        raise Exception(f"RPC Error: {response.status} {response.statusText}")

    return await response.json()


async def _call_realtime(func_name, args, kwargs):
    """
    Helper to send a fire-and-forget message via WebSocket.
    """
    payload = {"type": "realtime", "func": func_name, "args": args, "kwargs": kwargs}

    window.violetear_socket.send(json.dumps(payload))
