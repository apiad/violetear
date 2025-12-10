from __future__ import annotations

import abc
from dataclasses import dataclass
import io
from pathlib import Path
from typing import (
    Any,
    Callable,
    Iterable,
    List,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

import textwrap
from typing import Self
from violetear.dom import Event
from violetear.helpers import flatten
from violetear.style import Style
from violetear.stylesheet import StyleSheet


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


class ElementBuilder:
    """
    Helper class returned by the 'with element as e:' context manager.
    It allows creating siblings attached to the parent element using a fluent syntax.
    """
    def __init__(self, parent: Element):
        self._parent = parent

        # Register common HTML tags as methods on this instance
        # This allows: e.div(...), e.h1(...)
        self.div = self._factory("div")
        self.section = self._factory("section")
        self.header = self._factory("header")
        self.footer = self._factory("footer")
        self.main = self._factory("main")
        self.nav = self._factory("nav")

        self.h1 = self._factory("h1")
        self.h2 = self._factory("h2")
        self.h3 = self._factory("h3")
        self.h4 = self._factory("h4")
        self.h5 = self._factory("h5")
        self.h6 = self._factory("h6")

        self.p = self._factory("p")
        self.span = self._factory("span")
        self.a = self._factory("a")
        self.img = self._factory("img")

        self.ul = self._factory("ul")
        self.ol = self._factory("ol")
        self.li = self._factory("li")

        self.table = self._factory("table")
        self.thead = self._factory("thead")
        self.tbody = self._factory("tbody")
        self.tr = self._factory("tr")
        self.td = self._factory("td")
        self.th = self._factory("th")

        self.form = self._factory("form")
        self.input = self._factory("input")
        self.button = self._factory("button")
        self.label = self._factory("label")
        self.select = self._factory("select")
        self.option = self._factory("option")
        self.textarea = self._factory("textarea")

    def tag(self, name: str, *content, **kwargs) -> Element:
        """
        Explicitly create a tag that isn't pre-defined.
        Usage: e.tag("my-custom-component", ...)
        """
        el = Element(name, *content, **kwargs)
        self._parent.add(el)
        return el

    def _factory(self, tag_name: str):
        """
        Internal helper that returns a function to create a specific tag.
        """
        def wrapper(*content, **kwargs) -> Element:
            return self.tag(tag_name, *content, **kwargs)

        # improved debugging representation
        wrapper.__name__ = tag_name
        wrapper.__qualname__ = f"ElementBuilder.{tag_name}"
        return wrapper


class Element(Markup):
    def __init__(
        self,
        tag: str,
        text: str | None = None,
        *content: Element,
        classes: str | List[str] | None = None,
        id: str | None = None,
        style: Style | None = None,
        parent: Element | None = None,
        **attrs: str,
    ) -> None:
        self._tag = tag
        self._id = id
        self._text = text

        if isinstance(classes, str):
            classes = classes.split()

        self._classes = list(classes or [])
        self._content = []

        self.extend(*content)

        self._style = style or Style()
        self._parent = parent
        self._attrs = attrs

    def __enter__(self) -> ElementBuilder:
        """
        Enables the syntax:
        with doc.body as e:
            e.h1("Title")
        """
        return ElementBuilder(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Standard context manager exit.
        """
        return False  # Propagate exceptions if they occur

    def id(self, id: str) -> Self:
        self._id = id
        return self

    def classes(self, classes: Union[str, List[str]]) -> Self:
        if isinstance(classes, str):
            classes = classes.split()

        self._classes = classes
        return self

    def style(self, style: Style) -> Self:
        self._style = style
        return self

    def text(self, text: str) -> Self:
        self._text = text
        return self

    def attrs(self, **attrs) -> Element:
        self._attrs.update(attrs)
        return self

    def on(self, event: str, handler: Callable[[Event]]) -> Self:
        """
        Binds a python function to a DOM event.
        Serializes the function name to a data attribute.
        """
        print(handler)

        if not hasattr(handler, "__is_violetear_callback__"):
            raise ValueError("Event handler must be created with @app.client.callback")

        # We store it as a special attribute for the client runtime to find
        self._attrs[f"data-on-{event}"] = handler.__name__
        return self

    def has_bindings(self) -> bool:
        """Checks if this element or any child has a Python event binding."""
        # Check self
        for key in self._attrs:
            if key.startswith("data-on-"):
                return True

        # Check children
        for child in self._content:
            if isinstance(child, Element) and child.has_bindings():
                return True

        return False

    def _render(self, fp, indent: int):
        parts = [self._tag]

        if self._id:
            parts.append(f'id="{self._id}"')

        if self._classes:
            classes = " ".join(self._classes)
            parts.append(f'class="{classes}"')

        if self._style:
            parts.append(self._style.inline())

        for key, value in self._attrs.items():
            parts.append(f'{key}="{str(value)}"')

        tag_line = " ".join(parts)

        self._write_line(fp, f"<{tag_line}>", indent)

        if self._text:
            text = textwrap.indent(self._text, (indent + 1) * 4 * " ")
            fp.write(text)
            fp.write("\n")

        for child in self._content:
            child._render(fp, indent + 1)

        self._write_line(fp, f"</{self._tag}>", indent)

    def add(self, element: Element) -> Self:
        element._parent = self
        self._content.append(element)
        return self

    def extend(self, *elements: Element) -> Self:
        for el in flatten(elements):
            self.add(el)

        return self

    @overload
    def create(self, tag: str) -> Element:
        pass

    @overload
    def create[T: Element](self, clss: type[T]) -> T:
        pass

    def create[T: Element](  # type: ignore
        self,
        tag: str | type[T],
    ) -> T:
        if isinstance(tag, str):
            element = Element(tag)
        else:
            element = tag()  # type: ignore

        self.add(element)
        return cast(T, element)

    def spawn(
        self,
        count: Union[int, Iterable],
        tag: str,
    ) -> ElementSet:
        elements = []

        if isinstance(count, int):
            count = range(count)

        for index in count:
            elements.append((index, self.create(tag)))

        return ElementSet(elements, self)

    def parent(self) -> Element:
        return self._parent

    def root(self) -> Element:
        if self._parent is None:
            return self

        assert self._parent != self

        return self._parent.root()


class Component(Element, abc.ABC):
    def __init__(self) -> None:
        super().__init__(tag=None)

    @abc.abstractmethod
    def compose(self, content) -> Element:
        pass

    def _render(self, fp, indent: int):
        self.compose(self._content).root()._render(fp, indent)


class ElementSet:
    def __init__(self, elements: List[Tuple[Any, Element]], parent) -> None:
        self._elements = elements
        self._parent = parent

    def __iter__(self):
        return iter(self._elements)

    def each(self, fn: Callable[[int, Element]]) -> Self:
        for index, el in self._elements:
            fn(index, el)

        return self

    def parent(self) -> Element:
        return self._parent

    def root(self) -> Element:
        return self._parent.root()


@dataclass
class StyleResource:
    """
    Represents a CSS resource attached to a document.
    """

    sheet: StyleSheet | None = None
    href: str | None = None
    inline: bool = False


@dataclass
class ScriptResource:
    """
    Represents a JS script resource.
    """

    src: str | None = None
    content: str | None = None
    defer: bool = False
    module: bool = False


class Document(Markup):
    def __init__(self, lang: str = "en", **head_kwargs) -> None:
        self.lang = lang
        self.head = Head(**head_kwargs)
        self.body = Body()

    def style(
        self,
        sheet: StyleSheet | None = None,
        inline: bool = False,
        href: str | None = None,
    ) -> Document:
        if sheet is None and href is None:
            raise ValueError("Need either a sheet or an external href")

        if not inline and href is None:
            raise ValueError("Need an href when inline is False")

        if inline and sheet is None:
            raise ValueError("Need a sheet when inline is True")

        self.head.styles.append(
            StyleResource(
                sheet=sheet,
                href=href,
                inline=inline,
            )
        )

        return self

    def script(
        self,
        src: str | None = None,
        content: str | None = None,
        defer: bool = False,
        module: bool = False,
    ) -> Document:
        self.head.scripts.append(
            ScriptResource(
                src, textwrap.dedent(content) if content else None, defer, module
            )
        )
        return self

    def _render(self, fp, indent: int):
        self._write_line(fp, "<!DOCTYPE html>")
        self._write_line(fp, f'<html lang="{self.lang}">')
        self.head._render(fp, indent)
        self.body._render(fp, indent)
        self._write_line(fp, "</html>")


class Head(Markup):
    def __init__(
        self, charset: str = "UTF-8", title: str = "", favicon: str = "/favicon.ico"
    ) -> None:
        self.charset = charset
        self.title = title
        self.favicon = favicon
        self.styles: list[StyleResource] = []
        self.scripts: list[ScriptResource] = []

    def _render(self, fp, indent: int):
        self._write_line(fp, "<head>", indent)
        self._write_line(fp, f'<meta charset="{self.charset}">', indent + 1)
        self._write_line(
            fp, '<meta http-equiv="X-UA-Compatible" content="IE=edge">', indent + 1
        )
        self._write_line(
            fp,
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            indent + 1,
        )
        self._write_line(fp, f"<title>{self.title}</title>", indent + 1)

        # Render Favicon
        if self.favicon:
            self._write_line(fp, f'<link rel="icon" href="{self.favicon}">', indent + 1)

        for style in self.styles:
            if style.inline and style.sheet:
                # Render Inline
                self._write_line(fp, "<style>", indent + 1)
                self._write_line(fp, style.sheet.render(), indent + 1)
                self._write_line(fp, "</style>", indent + 1)

            elif style.href:
                # Render Link
                self._write_line(
                    fp, f'<link rel="stylesheet" href="{style.href}">', indent + 1
                )

        for script in self.scripts:
            if script.src:
                # External script
                attrs = f'src="{script.src}"'
                if script.defer:
                    attrs += " defer"
                if script.module:
                    attrs += ' type="module"'
                self._write_line(fp, f"<script {attrs}></script>", indent + 1)

            elif script.content:
                # Inline script
                attrs = ' type="module"' if script.module else ""
                self._write_line(fp, f"<script{attrs}>", indent + 1)
                self._write_line(fp, script.content, indent + 1)
                self._write_line(fp, "</script>", indent + 1)

        self._write_line(fp, "</head>", indent)


class Body(Element):
    def __init__(self, *classes) -> None:
        super().__init__("body", *classes)


def elfactory(tag: str):
    @staticmethod
    def element(
        *content: Element,
        text: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        style: Style | None = None,
        **attrs,
    ):
        return Element(
            tag, *content, text=text, id=id, classes=classes, style=style, **attrs
        )

    return element


class HTML:
    div = elfactory("div")
    h1 = elfactory("h1")
    h2 = elfactory("h2")
    h3 = elfactory("h3")
    h4 = elfactory("h4")
    h5 = elfactory("h5")
    h6 = elfactory("h6")
    li = elfactory("li")
    ol = elfactory("ol")
    p = elfactory("p")
    span = elfactory("span")
    ul = elfactory("ul")
    button = elfactory("button")
    input = elfactory("input")
