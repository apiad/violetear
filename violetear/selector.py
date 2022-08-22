from __future__ import annotations

import re

TOKEN_PART = r"[a-zA-Z0-9]+"
TOKEN = rf"({TOKEN_PART}\-)*{TOKEN_PART}"
TAG = rf"{TOKEN}"
ID = rf"\#{TOKEN}"
CLASSES = rf"\.{TOKEN}"
STATE = rf":{TOKEN}"
SELECTOR = rf"(?P<tag>{TAG})?(?P<id>{ID})?(?P<classes>({CLASSES})*)(?P<state>{STATE})?"


class Selector:
    def __init__(
        self,
        tag: str = None,
        id: str = None,
        classes: str = (),
        state: str = None,
        *,
        parent: Selector = None,
    ) -> None:
        self._id = id
        self._tag = tag
        self._classes = classes
        self._state = state
        self._parent = parent

    def css(self) -> str:
        parts = []

        if self._parent:
            parts.append(self._parent.css())
            parts.append(">")

        if self._tag:
            parts.append(self._tag)

        if self._id:
            parts.append(f"#{self._id}")

        for cls in self._classes:
            parts.append(f".{cls}")

        if self._state:
            parts.append(f":{self._state}")

        return "".join(parts)

    def on(self, state) -> Selector:
        return Selector(self._tag, self._id, self._classes, state, parent=self._parent)

    def children(self, selector: str, *, nth: int = None) -> Selector:
        s = Selector.from_css(selector, parent=self)

        if nth is not None:
            s = s.on(f"nth-child({nth})")

        return s

    def __str__(self) -> str:
        return self.css()

    def __repr__(self) -> str:
        return f"Selector(tag={repr(self._tag)}, id={repr(self._id)}, classes={repr(self._classes)}, state={repr(self._state)})"

    def markup(self) -> str:
        parts = []

        if self._id:
            parts.append(f'id="{self._id}"')

        if self._classes:
            classes = " ".join(self._classes)
            parts.append(f'class="{classes}"')

        return " ".join(parts)

    @classmethod
    def from_css(cls, selector: str = "*", *, parent: Selector = None) -> Selector:
        match = re.match(SELECTOR, selector)

        if not match:
            raise ValueError(f"Invalid CSS selector: {selector}")

        tag = match.group("tag")
        id = match.group("id")

        if id:
            id = id[1:]

        classes = match.group("classes")

        if classes:
            classes = classes.split(".")[1:]
        else:
            classes = []

        state = match.group("state")

        if state:
            state = state[1:]

        return Selector(tag, id, classes, state, parent=parent)
