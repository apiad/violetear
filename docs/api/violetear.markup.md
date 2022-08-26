<a name="ref:Markup"></a>
<a name="ref:Element"></a>
<a name="ref:Page"></a>
<a name="ref:Head"></a>
<a name="ref:Body"></a>

```python linenums="1"
from __future__ import annotations

import abc
from ast import Call
import io
from pathlib import Path
from typing import Any, Callable, List

import textwrap
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
        classes: List[str] = None,
        id: str = None,
        style: Style = None,
        parent: Element = None,
    ) -> None:
        self.tag = tag
        self.id = id
        self.text = text

        if isinstance(classes, str):
            classes = classes.split()

        self.classes = list(classes or [])
        self.content = list(content)
        self.style = style or Style()
        self._parent = parent

    def _render(self, fp, indent: int):
        parts = [self.tag]

        if self.id:
            parts.append(f'id="{self.id}"')

        if self.classes:
            classes = " ".join(self.classes)
            parts.append(f'class="{classes}"')

        if self.style:
            parts.append(self.style.inline())

        tag_line = " ".join(parts)

        self._write_line(fp, f"<{tag_line}>", indent)

        if self.text:
            text = textwrap.indent(self.text, (indent + 1) * 4 * " ")
            fp.write(text)
            fp.write("\n")

        for child in self.content:
            child._render(fp, indent + 1)

        self._write_line(fp, f"</{self.tag}>", indent)

    def add(self, element: Element) -> Element:
        element._parent = self
        self.content.append(element)
        return self

    def create(
        self,
        tag: str,
        classes: List[str] = None,
        id: str = None,
        style: Style = None,
        text: str = None,
    ) -> Element:
        element = Element(tag, classes=classes, id=id, style=style, text=text)
        self.add(element)
        return element

    def spawn(
        self,
        count: int,
        tag: str,
        classes: List[str] = None,
        id: str = None,
        style: Style = None,
        text: str = None,
    ) -> Element:
        for i in range(count):
            if callable(classes):
                _classes = classes(i)
            else:
                _classes = classes

            if callable(id):
                _id = id(i)
            else:
                _id = id

            if callable(style):
                _style = style(i)
            else:
                _style = style

            if callable(text):
                _text = text(i)
            else:
                _text = text

            self.create(tag, classes=_classes, id=_id, style=_style, text=_text)

        return self

    def styled(self, fn: Callable[[Style]]) -> Element:
        fn(self.style)
        return self

    def parent(self) -> Element:
        return self._parent


class Page(Markup):
    def __init__(self, lang: str = "en", **head_kwargs) -> None:
        self.lang = lang
        self.head = Head(**head_kwargs)
        self.body = Body()
        self.styles = []

    def style(self, sheet: StyleSheet, inline: bool = False, name: str = None) -> Page:
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
```

