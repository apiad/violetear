"""
Violetear Client Runtime.
This code runs inside the browser (Pyodide) to bring the static HTML to life.
"""

import sys
import json
import asyncio

# We define IS_BROWSER to avoid import errors if this is imported on the server
IS_BROWSER = "pyodide" in sys.modules or "emscripten" in sys.platform


def hydrate(namespace: dict):
    """
    Scans the DOM for Violetear interactive elements and binds them to
    Python functions found in the provided namespace.

    Args:
        namespace: A dictionary mapping function names to callables.
                   Typically, you pass `globals()` here from your client script.
    """
    if not IS_BROWSER:
        raise TypeError("Hydration called outside of browser environment. Skipping.")

    from js import document
    from pyodide.ffi import create_proxy

    # We explicitly scan for common events.
    # In the future, we could inspect the DOM more aggressively or use a MutationObserver.
    supported_events = [
        "click",
        "change",
        "input",
        "submit",
        "keydown",
        "keyup",
        "mouseenter",
        "mouseleave",
    ]

    bound_count = 0

    for event_name in supported_events:
        # The markup generates attributes like: data-py-on-click="my_func"
        attr = f"data-on-{event_name}"
        selector = f"[{attr}]"

        elements = document.querySelectorAll(selector)

        for element in elements:
            handler_name = element.getAttribute(attr)

            if handler_name in namespace:
                handler_func = namespace[handler_name]

                # 1. Create a Pyodide Proxy
                # We wrap the python function so JS can call it safely.
                # 'create_proxy' ensures the function isn't garbage collected immediately.
                proxy = create_proxy(handler_func)

                # 2. Bind the Listener
                # We attach the Python proxy directly to the JS event listener
                element.addEventListener(event_name, proxy)

                # 3. Cleanup (Optional)
                # We remove the data attribute so we don't double-bind if hydrate is called again
                element.removeAttribute(attr)

                bound_count += 1
            else:
                print(
                    f"[Violetear] Warning: Function '{handler_name}' not found for event '{event_name}'"
                )

    print(f"[Violetear] Hydrated {bound_count} interactive elements.")
    setup_socket_listener(namespace)


def setup_socket_listener(namespace):
    """
    Connects to the server and listens for RPC commands.
    """
    from js import WebSocket, window

    # Calculate the WebSocket URL (ws:// or wss://)
    protocol = "wss" if window.location.protocol == "https:" else "ws"
    ws_url = f"{protocol}://{window.location.host}/_violetear/ws"

    socket = WebSocket.new(ws_url)

    def on_message(event):
        data = json.loads(event.data)

        if data.get("type") == "rpc":
            func_name = data["func"]
            args = data["args"]
            kwargs = data["kwargs"]

            # 1. Look up the function in the global scope
            if func_name in namespace:
                func = namespace[func_name]

                # 2. Schedule the async function to run on the event loop
                # We use asyncio.create_task because we are inside a sync callback
                asyncio.create_task(func(*args, **kwargs))
            else:
                print(f"[Violetear] Received RPC for unknown function: {func_name}")

    # Attach the callback (converting Python function to JS proxy not strictly needed for simple events in recent Pyodide, but good practice)
    socket.onmessage = on_message

    # Keep a reference so it doesn't get garbage collected
    window.violetear_socket = socket

    print("[Violetear] Attached socket connection")
