from __future__ import annotations

import abc
import io
from pathlib import Path
from typing import Any, Callable, Iterable, List, Tuple, Union

import textwrap
from typing_extensions import Self
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


class Element(Markup):
    def __init__(
        self,
        tag: str,
        *content: Element,
        text: str = None,
        classes: Union[str, List[str]] = None,
        id: str = None,
        style: Style = None,
        parent: Element = None,
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

    def create(
        self,
        tag: str,
    ) -> Element:
        element = Element(tag)
        self.add(element)
        return element

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
    def compose(self) -> Element:
        pass

    def _render(self, fp, indent: int):
        self.compose().root()._render(fp, indent)


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


class Document(Markup):
    def __init__(self, lang: str = "en", **head_kwargs) -> None:
        self.lang = lang
        self.head = Head(**head_kwargs)
        self.body = Body()
        self.styles = []

    def style(
        self, sheet: StyleSheet, inline: bool = False, name: str = None
    ) -> Document:
        if not inline and name is None:
            raise ValueError("Need a name when inline is false")

        if inline:
            self.styles.append(sheet)
        else:
            self.head.styles.append((sheet, name))

        return self

    def _render(self, fp, indent: int):
        self._write_line(fp, "<!DOCTYPE html>")
        self._write_line(fp, f'<html lang="{self.lang}">')
        self.head._render(fp, indent)
        self.body._render(fp, indent)
        self._write_line(fp, "</html>")


class Head(Markup):
    def __init__(self, charset: str = "UTF-8", title: str = "") -> None:
        self.charset = charset
        self.title = title
        self.styles = []

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

        for sheet, name in self.styles:
            self._write_line(fp, f'<link rel="stylesheet" href="{name}">', indent + 1)
            sheet.render(name)

        self._write_line(fp, "</head>", indent)


class Body(Element):
    def __init__(self, *classes) -> None:
        super().__init__("body", *classes)
