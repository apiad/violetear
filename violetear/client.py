"""
Violetear Client Runtime.
This code runs inside the browser (Pyodide) to bring the static HTML to life.
"""

import sys

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
