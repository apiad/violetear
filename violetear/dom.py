import sys
from typing import Optional, Callable, Protocol, Union, List, Any

# Environment Check
IS_BROWSER = "pyodide" in sys.modules or "emscripten" in sys.platform

if IS_BROWSER:
    from js import document, console
    from pyodide.ffi import create_proxy
else:
    # On the server, we don't strictly raise ImportError anymore to allow
    # safe imports, but we disable functionality.
    pass


class DOMElement:
    """
    A Client-Side wrapper around a JS DOM Element.
    Provides a fluent, Pythonic API for DOM manipulation.
    """

    def __init__(self, js_element):
        self._el = js_element
        # Track active bindings to prevent "Zombie Updates"
        # Maps property_name -> cleanup_function
        self._active_bindings = {}

    def _bind_property(self, prop_name: str, proxy_obj):
        """
        Helper: Binds a specific DOM property to a State Proxy.
        Removes any existing binding on that property first.
        """
        if not IS_BROWSER:
            return

        # 1. Unbind previous owner if exists
        if prop_name in self._active_bindings:
            self._active_bindings[prop_name]()
            del self._active_bindings[prop_name]

        # 2. Bind new owner
        # Lazy import to avoid circular dependencies
        from violetear.client import ReactiveRegistry

        # We define a specialized updater based on the property name
        updater = self._get_updater_for_prop(prop_name)

        # Register and store the cleanup function
        # We bind to the proxy's PATH
        unsubscribe = ReactiveRegistry.bind(proxy_obj._path, updater)
        self._active_bindings[prop_name] = unsubscribe

    def _get_updater_for_prop(self, prop: str):
        """Returns a lambda that knows how to update the specific DOM property."""
        if prop == "innerText":
            return lambda val: setattr(self._el, "innerText", str(val))
        elif prop == "innerHTML":
            return lambda val: setattr(self._el, "innerHTML", str(val))
        elif prop == "value":
            return lambda val: setattr(self._el, "value", str(val))
        elif prop.startswith("style."):
            style_name = prop.split(".")[1]
            return lambda val: self._el.style.setProperty(style_name, str(val))
        elif prop.startswith("attr."):
            attr_name = prop.split(".")[1]
            return lambda val: self._el.setAttribute(attr_name, str(val))
        elif prop.startswith("prop."):
            prop_name = prop.split(".")[1]
            return lambda val: setattr(self._el, prop_name, val)
        return lambda val: None

    @property
    def text(self) -> str:
        if IS_BROWSER and self._el:
            return self._el.innerText
        return ""

    @text.setter
    def text(self, content: Any):
        """Sets innerText. Supports Reactive Binding."""
        if IS_BROWSER and self._el:
            # Check for Proxy (duck typing)
            if hasattr(content, "_path") and hasattr(content, "current_value"):
                self._bind_property("innerText", content)
                self._el.innerText = str(content.current_value)
            else:
                # Manual assignment? Clear old bindings!
                if "innerText" in self._active_bindings:
                    self._active_bindings["innerText"]()
                    del self._active_bindings["innerText"]
                self._el.innerText = str(content)

    def html(self, content: Any) -> "DOMElement":
        """Sets innerHTML. Supports Reactive Binding."""
        if IS_BROWSER and self._el:
            if hasattr(content, "_path") and hasattr(content, "current_value"):
                self._bind_property("innerHTML", content)
                self._el.innerHTML = str(content.current_value)
            else:
                if "innerHTML" in self._active_bindings:
                    self._active_bindings["innerHTML"]()
                self._el.innerHTML = str(content)
        return self

    @property
    def value(self) -> Any:
        if IS_BROWSER and self._el:
            return self._el.value
        return object()

    @value.setter
    def value(self, value: Any):
        """Sets value. Supports Reactive Binding."""
        if IS_BROWSER and self._el:
            if hasattr(value, "_path") and hasattr(value, "current_value"):
                self._bind_property("value", value)
                self._el.value = str(value.current_value)
            else:
                if "value" in self._active_bindings:
                    self._active_bindings["value"]()
                self._el.value = str(value)

    def style(self, **kwargs) -> "DOMElement":
        """
        Sets CSS styles. Supports Reactive Binding per property.
        """
        if IS_BROWSER and self._el:
            for k, v in kwargs.items():
                key = k.replace("_", "-")

                if hasattr(v, "_path") and hasattr(v, "current_value"):
                    # Bind specific style property
                    self._bind_property(f"style.{key}", v)
                    self._el.style.setProperty(key, str(v.current_value))
                else:
                    # Manual set - should technically unbind that specific style,
                    # but granular style unbinding is complex.
                    # For now, we just overwrite.
                    self._el.style.setProperty(key, str(v))
        return self

    def add(self, *classes: str) -> "DOMElement":
        if IS_BROWSER and self._el:
            for cls in classes:
                self._el.classList.add(cls)
        return self

    def remove(self, *classes: str) -> "DOMElement":
        if IS_BROWSER and self._el:
            for cls in classes:
                self._el.classList.remove(cls)
        return self

    def on(self, event: str, handler: Callable) -> "DOMElement":
        """Attaches a Python event listener."""
        if IS_BROWSER and self._el:
            proxy = create_proxy(handler)
            self._el.addEventListener(event, proxy)
        return self

    def click(self, handler: Callable) -> "DOMElement":
        return self.on("click", handler)

    def append(self, element: "DOMElement") -> "DOMElement":
        if IS_BROWSER and self._el and element._el:
            self._el.appendChild(element._el)
        return self

    def attr(self, name: str, value: Any = None) -> Union[str, "DOMElement", None]:
        """Get or Set attribute. Supports Binding."""
        if IS_BROWSER and self._el:
            if value is None:
                return self._el.getAttribute(name)

            if hasattr(value, "_path") and hasattr(value, "current_value"):
                self._bind_property(f"attr.{name}", value)
                self._el.setAttribute(name, str(value.current_value))
            else:
                self._el.setAttribute(name, str(value))
            return self
        return self if value is not None else None

    def prop(self, name: str, value: Any = None) -> Any:
        """Get or Set JS Property. Supports Binding."""
        if IS_BROWSER and self._el:
            if value is None:
                return getattr(self._el, name, None)

            if hasattr(value, "_path") and hasattr(value, "current_value"):
                self._bind_property(f"prop.{name}", value)
                setattr(self._el, name, value.current_value)
            else:
                setattr(self._el, name, value)
            return self
        return self if value is not None else None

    # ... (toggle, serialize, and DOM static class remain unchanged) ...
    def toggle(self, cls: str, force: Optional[bool] = None) -> "DOMElement":
        if IS_BROWSER and self._el:
            if force is True:
                self._el.classList.add(cls)
            elif force is False:
                self._el.classList.remove(cls)
            else:
                if self._el.classList.contains(cls):
                    self._el.classList.remove(cls)
                else:
                    self._el.classList.add(cls)
        return self

    def serialize(self) -> dict:
        data = {}
        if IS_BROWSER and self._el:
            inputs = self._el.querySelectorAll("input, select, textarea")
            for i in range(inputs.length):
                el = inputs.item(i)
                name = el.name
                if not name: continue
                if el.type == "checkbox":
                    if el.checked: data[name] = True
                elif el.type == "radio":
                    if el.checked: data[name] = el.value
                else:
                    data[name] = el.value
        return data

class DOM:
    @staticmethod
    def find(id: str) -> DOMElement:
        if IS_BROWSER:
            el = document.getElementById(id)
            if not el:
                # console.warn(f"Violetear: Element with id='{id}' not found")
                return DOMElement(None)
            return DOMElement(el)
        return DOMElement(None)

    @staticmethod
    def query(selector: str) -> List[DOMElement]:
        if IS_BROWSER:
            els = document.querySelectorAll(selector)
            return [DOMElement(e) for e in els]
        return []

    @staticmethod
    def create(tag: str) -> DOMElement:
        if IS_BROWSER:
            return DOMElement(document.createElement(tag))
        return DOMElement(None)

    @staticmethod
    def body() -> DOMElement:
        if IS_BROWSER:
            return DOMElement(document.body)
        return DOMElement(None)

class ProxyElement(Protocol):
    """
    Lightweight protocol for typing DOM elements
    """

    id: str
    classes: list[str]
    value: Any


class Event(Protocol):
    """
    Lightweight protocol for typing DOM events
    """

    target: ProxyElement
