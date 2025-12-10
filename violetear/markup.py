from __future__ import annotations
import abc
import io
import textwrap
from typing import List, Union, Callable, Self, Any, Optional
from pathlib import Path


class Markup(abc.ABC):
    @abc.abstractmethod
    def _render(self, fp, indent: int):
        pass

    def render(self, fp=None, indent: int = 0):
        opened = False
        result = None

        if isinstance(fp, (str, Path)):
            fp = open(fp, "w")
            opened = True

        elif fp is None:
            fp = io.StringIO()
            opened = True

        self._render(fp, indent)

        if isinstance(fp, io.StringIO):
            result = fp.getvalue()

        if opened:
            fp.close()

        return result

    def _write_line(self, fp, value, indent=0):
        value = textwrap.indent(str(value), indent * 4 * " ")
        if not value.endswith("\n"):
            value += "\n"
        fp.write(value)


class Element(Markup):
    def __init__(self, tag: str, *content, text: str | None = None, **attrs):
        self._tag = tag
        self._content = []
        self._text = text
        self._attrs = attrs
        self._classes = []
        self._style = None
        self._id = attrs.pop("id", None)

        # Handle class passed as kwarg
        if "classes" in attrs:
            self.classes(attrs.pop("classes"))

        self.extend(*content)

    def __enter__(self) -> ElementBuilder:
        """
        Returns a Builder attached to this element.
        Usage: with doc.body as e: e.div(...)
        """
        return ElementBuilder(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def id(self, id: str) -> Self:
        self._id = id
        return self

    def classes(self, classes: Union[str, List[str]]) -> Self:
        if isinstance(classes, str):
            classes = classes.split()
        self._classes = classes
        return self

    def style(self, style: Any) -> Self:
        self._style = style
        return self

    def on(self, event: str, handler: Callable) -> Self:
        if not hasattr(handler, "__is_violetear_callback__"):
            raise ValueError("Event handler must be created with @app.client.callback")
        self._attrs[f"data-on-{event}"] = handler.__name__
        return self

    def add(self, element: Element) -> Self:
        self._content.append(element)
        return self

    def extend(self, *elements) -> Self:
        for el in elements:
            self.add(el)
        return self

    def _render(self, fp, indent: int):
        parts = [self._tag]
        if self._id:
            parts.append(f'id="{self._id}"')
        if self._classes:
            parts.append(f'class="{" ".join(self._classes)}"')
        if self._style:
            parts.append(self._style.inline())
        for k, v in self._attrs.items():
            parts.append(f'{k}="{v}"')

        self._write_line(fp, f"<{' '.join(parts)}>", indent)
        if self._text:
            fp.write(textwrap.indent(self._text, (indent + 1) * 4 * " ") + "\n")
        for child in self._content:
            child._render(fp, indent + 1)
        self._write_line(fp, f"</{self._tag}>", indent)


class ElementBuilder:
    """
    The Universal Builder.

    1. When initialized with a parent (via __enter__), it creates elements
       and automatically appends them to that parent.

    2. When initialized without a parent (the 'HTML' singleton), it creates
       orphaned elements suitable for composition or root nodes.
    """

    def __init__(self, parent: Optional[Element] = None):
        self._parent = parent

    def tag(self, name: str, *content, **kwargs) -> Element:
        el = Element(name, *content, **kwargs)

        # KEY LOGIC: Only attach if we have a parent
        if self._parent:
            self._parent.add(el)

        return el

    # --- Explicit Methods for Intellisense ---
    def div(self, *c, **k) -> Element:
        return self.tag("div", *c, **k)

    def section(self, *c, **k) -> Element:
        return self.tag("section", *c, **k)

    def article(self, *c, **k) -> Element:
        return self.tag("article", *c, **k)

    def header(self, *c, **k) -> Element:
        return self.tag("header", *c, **k)

    def footer(self, *c, **k) -> Element:
        return self.tag("footer", *c, **k)

    def main(self, *c, **k) -> Element:
        return self.tag("main", *c, **k)

    def nav(self, *c, **k) -> Element:
        return self.tag("nav", *c, **k)

    def aside(self, *c, **k) -> Element:
        return self.tag("aside", *c, **k)

    def h1(self, *c, **k) -> Element:
        return self.tag("h1", *c, **k)

    def h2(self, *c, **k) -> Element:
        return self.tag("h2", *c, **k)

    def h3(self, *c, **k) -> Element:
        return self.tag("h3", *c, **k)

    def h4(self, *c, **k) -> Element:
        return self.tag("h4", *c, **k)

    def h5(self, *c, **k) -> Element:
        return self.tag("h5", *c, **k)

    def h6(self, *c, **k) -> Element:
        return self.tag("h6", *c, **k)

    def p(self, *c, **k) -> Element:
        return self.tag("p", *c, **k)

    def span(self, *c, **k) -> Element:
        return self.tag("span", *c, **k)

    def a(self, *c, **k) -> Element:
        return self.tag("a", *c, **k)

    def img(self, *c, **k) -> Element:
        return self.tag("img", *c, **k)

    def br(self, *c, **k) -> Element:
        return self.tag("br", *c, **k)

    def hr(self, *c, **k) -> Element:
        return self.tag("hr", *c, **k)

    def ul(self, *c, **k) -> Element:
        return self.tag("ul", *c, **k)

    def ol(self, *c, **k) -> Element:
        return self.tag("ol", *c, **k)

    def li(self, *c, **k) -> Element:
        return self.tag("li", *c, **k)

    def table(self, *c, **k) -> Element:
        return self.tag("table", *c, **k)

    def thead(self, *c, **k) -> Element:
        return self.tag("thead", *c, **k)

    def tbody(self, *c, **k) -> Element:
        return self.tag("tbody", *c, **k)

    def tr(self, *c, **k) -> Element:
        return self.tag("tr", *c, **k)

    def td(self, *c, **k) -> Element:
        return self.tag("td", *c, **k)

    def th(self, *c, **k) -> Element:
        return self.tag("th", *c, **k)

    def form(self, *c, **k) -> Element:
        return self.tag("form", *c, **k)

    def input(self, *c, **k) -> Element:
        return self.tag("input", *c, **k)

    def button(self, *c, **k) -> Element:
        return self.tag("button", *c, **k)

    def label(self, *c, **k) -> Element:
        return self.tag("label", *c, **k)

    def select(self, *c, **k) -> Element:
        return self.tag("select", *c, **k)

    def option(self, *c, **k) -> Element:
        return self.tag("option", *c, **k)

    def textarea(self, *c, **k) -> Element:
        return self.tag("textarea", *c, **k)

    def iframe(self, *c, **k) -> Element:
        return self.tag("iframe", *c, **k)

    def script(self, *c, **k) -> Element:
        return self.tag("script", *c, **k)

    def style(self, *c, **k) -> Element:
        return self.tag("style", *c, **k)

    def meta(self, *c, **k) -> Element:
        return self.tag("meta", *c, **k)

    def link(self, *c, **k) -> Element:
        return self.tag("link", *c, **k)


# --- SINGLETON INSTANCE ---
# This replaces the 'class HTML' static factory.
# It uses the exact same 'ElementBuilder' logic but has no parent,
# so tags created by it are not auto-appended to anything.
HTML = ElementBuilder(parent=None)
