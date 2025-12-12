import asyncio
import json
import uuid
import sys

# We use a try/except block for these imports so this file
# doesn't crash if imported in a non-browser environment (like for testing).
try:
    from js import document, window, WebSocket, console, Object # type: ignore
    from pyodide.ffi import create_proxy, to_js # type: ignore
except ImportError:
    pass

from violetear.storage import session

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
    def bind(path: str, callback: callable):
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
                    console.error(f"[Violetear] Error in reactive update for '{path}': {str(e)}")


# --- HYDRATION LOGIC ---

def hydrate(scope):
    """
    Bootstraps the application in the browser.
    1. Scans DOM for Event Listeners (data-on-*)
    2. Scans DOM for Reactive Bindings (data-bind-*)
    3. Connects Websockets
    """

    # 1. Event Listeners (Original Logic)
    _hydrate_events(scope)

    # 2. Reactive Bindings (New Logic)
    _hydrate_bindings(scope)

    # 3. Networking
    setup_socket_listener(scope)


def _hydrate_bindings(scope):
    """
    Scans the DOM for 'data-bind-[attr]="State.Path"'.
    Connects the DOM element to the ReactiveRegistry.
    """
    elements = document.querySelectorAll("*")

    for i in range(elements.length):
        el = elements.item(i)

        # Iterate over all attributes of the element
        # attributes is a NamedNodeMap, we need to be careful iterating it
        for attr in list(el.attributes):
            name = attr.name # e.g. "data-bind-class"
            path = attr.value # e.g. "UiState.theme"

            if name.startswith("data-bind-"):
                # Extract the target property: "class", "text", "style.display"
                target_prop = name.replace("data-bind-", "")

                # Create a specific updater for this element and property
                updater = _create_dom_updater(el, target_prop)

                # Register with the Registry
                # Note: Hydration bindings are usually permanent for the page life,
                # so we don't strictly need to capture the unsubscribe handle here,
                # unless we plan to support removing these elements dynamically later.
                ReactiveRegistry.bind(path, updater)


def _create_dom_updater(el, prop):
    """
    Factory that returns a callback function to update a specific DOM node.
    """

    # Strategy pattern for different binding types
    if prop == "text":
        return lambda val: setattr(el, "innerText", str(val))

    elif prop == "html":
        return lambda val: setattr(el, "innerHTML", str(val))

    elif prop == "value":
        # For input fields
        return lambda val: setattr(el, "value", str(val))

    elif prop == "class":
        # Replaces the entire class string (be careful!)
        # Better strategy: 'data-bind-class-active="Ui.isActive"'
        return lambda val: setattr(el, "className", str(val))

    else:
        # Default: Set as an attribute (e.g. src, href, disabled)
        # Handle boolean attributes for accessibility
        def attr_updater(val):
            if val is False or val is None:
                el.removeAttribute(prop)
            else:
                el.setAttribute(prop, str(val))
        return attr_updater


def _hydrate_events(scope):
    """
    Scans for [data-on-event] and attaches python handlers.
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
        for attr in list(el.attributes):
            name = attr.name
            if name.startswith("data-on-"):
                event_name = name.replace("data-on-", "")
                func_name = attr.value

                handler = create_handler(func_name)
                proxy = create_proxy(handler)

                # Prevent GC
                if not hasattr(el, "_py_listeners"):
                    el._py_listeners = []
                el._py_listeners.append(proxy)

                el.addEventListener(event_name, proxy)


# --- NETWORKING & RPC (Existing Logic) ---

def get_client_id():
    client_id = session.get("VIOLETEAR_ID")
    if client_id is None:
        client_id = str(uuid.uuid4())
        session["VIOLETEAR_ID"] = client_id
    return client_id

def get_socket_url():
    protocol = "wss" if window.location.protocol == "https:" else "ws"
    host = window.location.host
    client_id = get_client_id()
    return f"{protocol}://{host}/_violetear/ws?client_id={client_id}"

def setup_socket_listener(scope):
    url = get_socket_url()
    socket = WebSocket.new(url)

    def on_message(event):
        try:
            data = json.loads(event.data)
            if data.get("type") == "rpc":
                func_name = data["func"]
                args = data.get("args", [])
                kwargs = data.get("kwargs", {})
                if func_name in scope:
                    func = scope[func_name]
                    asyncio.create_task(func(*args, **kwargs))
                else:
                    console.warn(f"[Violetear] Function '{func_name}' not found.")
        except Exception as e:
            console.error(f"[Violetear] RPC Error: {str(e)}")

    def on_close(event):
        # simple reconnect logic
        retry = create_proxy(lambda: setup_socket_listener(scope))
        window.setTimeout(retry, 3000)

    socket.onmessage = create_proxy(on_message)
    socket.onclose = create_proxy(on_close)
    window.violetear_socket = socket

async def _call_rpc(func_name, arg_names, args, kwargs):
    from pyodide.http import pyfetch
    payload = {k: v for k, v in zip(arg_names, args)}
    payload.update(kwargs)
    response = await pyfetch(
        f"/_violetear/rpc/{func_name}",
        method="POST",
        headers={"Content-Type": "application/json"},
        body=json.dumps(payload),
    )
    if not response.ok:
        raise Exception(f"RPC Error: {response.status}")
    return await response.json()

async def _call_realtime(func_name, args, kwargs):
    payload = {"type": "realtime", "func": func_name, "args": args, "kwargs": kwargs}
    window.violetear_socket.send(json.dumps(payload))