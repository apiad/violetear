import re

TOKEN_PART = r"[a-zA-Z0-9]+"
TOKEN = rf"({TOKEN_PART}\-)*{TOKEN_PART}"
TAG = rf"{TOKEN}"
ID = rf"\#{TOKEN}"
CLASSES = rf"\.{TOKEN}"
SELECTOR = rf"(?P<tag>{TAG})?(?P<id>{ID})?(?P<classes>({CLASSES})*)"

class Selector:
    def __init__(self, tag: str = None, id: str = None, *classes: str) -> None:
        self._id = id
        self._tag = tag
        self._classes = classes

    def css(self) -> str:
        parts = []

        if self._tag:
            parts.append(self._tag)

        if self._id:
            parts.append(f"#{self._id}")

        for cls in self._classes:
            parts.append(f".{cls}")

        return "".join(parts)

    def __str__(self) -> str:
        return self.css()

    def __repr__(self) -> str:
        return f"Selector(tag={repr(self._tag)}, id={repr(self._id)}, classes={repr(self._classes)})"

    def markup(self) -> str:
        parts = []

        if self._tag:
            parts.append(self._tag)

        if self._id:
            parts.append(f'id="{self._id}"')

        if self._classes:
            classes = ' '.join(self._classes)
            parts.append(f'class="{classes}"')

        return " ".join(parts)

    @classmethod
    def from_css(cls, selector:str) -> "Selector":
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

        return Selector(tag, id, *classes)
