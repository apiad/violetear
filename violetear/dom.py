import sys
from typing import Optional, Callable, Protocol, Union, List, Any

# Environment Check
IS_BROWSER = "pyodide" in sys.modules or "emscripten" in sys.platform

if IS_BROWSER:
    from js import document, console
    from pyodide.ffi import create_proxy


class DOMElement:
    """
    A Client-Side wrapper around a JS DOM Element.
    Provides a fluent, Pythonic API for DOM manipulation.
    """

    def __init__(self, js_element):
        self._el = js_element

    @property
    def text(self) -> str:
        if IS_BROWSER and self._el:
            return self._el.innerText

        return ""

    @text.setter
    def text(self, content: str):
        """Sets innerText."""
        if IS_BROWSER and self._el:
            self._el.innerText = str(content)

    def html(self, content: str) -> "DOMElement":
        """Sets innerHTML."""
        if IS_BROWSER and self._el:
            self._el.innerHTML = str(content)
        return self

    @property
    def value(self) -> Any:
        """
        Gets the current value.
        """
        if IS_BROWSER and self._el:
            return self._el.value

        return object()

    @value.setter
    def value(self, value: str):
        """
        Sets the value
        """
        if IS_BROWSER and self._el:
            self._el.value = str(value)

    def style(self, **kwargs) -> "DOMElement":
        """
        Sets CSS styles using snake_case or kebab-case.
        Example: .style(background_color="red", margin_top="10px")
        """
        if IS_BROWSER and self._el:
            for k, v in kwargs.items():
                key = k.replace("_", "-")
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

    def toggle(self, *classes: str) -> "DOMElement":
        if IS_BROWSER and self._el:
            for cls in classes:
                if cls in self._el.classList:
                    self._el.classList.remove(cls)
                else:
                    self._el.classList.add(cls)
        return self

    def on(self, event: str, handler: Callable) -> "DOMElement":
        """Attaches a Python event listener."""
        if IS_BROWSER and self._el:
            # Create a persistent proxy for the handler
            proxy = create_proxy(handler)
            self._el.addEventListener(event, proxy)
        return self

    def click(self, handler: Callable) -> "DOMElement":
        """Shorthand for .on('click', ...)"""
        return self.on("click", handler)

    def append(self, element: "DOMElement") -> "DOMElement":
        if IS_BROWSER and self._el and element._el:
            self._el.appendChild(element._el)
        return self

    @property
    def raw(self):
        """Returns the underlying JS element."""
        return self._el


class Document:
    """
    Static entry point for DOM selection.
    """

    @staticmethod
    def find(id: str) -> DOMElement:
        """Finds a single element by ID."""
        if IS_BROWSER:
            el = document.getElementById(id)
            if not el:
                console.warn(f"Violetear: Element with id='{id}' not found")
                # Return a dummy wrapper to prevent crashes on chaining
                return DOMElement(None)
            return DOMElement(el)
        return DOMElement(None)

    @staticmethod
    def query(selector: str) -> List[DOMElement]:
        """Finds all elements matching a CSS selector."""
        if IS_BROWSER:
            els = document.querySelectorAll(selector)
            return [DOMElement(e) for e in els]
        return []

    @staticmethod
    def create(tag: str) -> DOMElement:
        """Creates a new detached element."""
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


class Event(Protocol):
    """
    Lightweight protocol for typing DOM events
    """

    target: ProxyElement
