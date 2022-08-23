# # Selectors

"""This module defines the `Selector` class which represents a CSS selector.

Selectors are used in the `Style` class to define the elements a style applies.
"""

from __future__ import annotations
from typing import Dict

import re

# The CSS selector language is somewhat large, so we will not even attempt a full coverage.
# Instead, we will solve the most common patterns: a single selector with tag, id, classes, states and attributes.
# Things like multiple comma-separated selectors are not in our interest at least so far.

# ## A subset of the CSS selector language

# We will begin by defining a simple regular expression to cover these cases.
# I know, regexes, right?
# However, this one will be simple, I promise.

# We define a simple token as something that can have alphanumeric characters in kebab-case.
# So things like `some-tag` are valid tokens.

TOKEN_PART = r"[a-zA-Z0-9]+"
TOKEN = rf"({TOKEN_PART}\-)*{TOKEN_PART}"

# Based on this simple definition, now all we need is several regexes for each of the sub-patterns
# we can find in a CSS string.

# A simple tag like `div` or `span`:
TAG = rf"{TOKEN}"

# An id like `#main`:
ID = rf"\#{TOKEN}"

# A single class like `.bar`:
CLASSES = rf"\.{TOKEN}"

# A single state like `:hover`:
STATE = rf":{TOKEN}"

# A single attribute like `[state=on]`
ATTRIBUTE = rf"\[{TOKEN}={TOKEN}\]"


# And finally, we combine all those regex patterns into a single regex string that has:

# - one optional tag,
# - one optional id,
# - zero or more classes,
# - zero or more states, and
# - zero or more attributes.

SELECTOR = rf"(?P<tag>{TAG})?(?P<id>{ID})?(?P<classes>({CLASSES})*)(?P<states>({STATE})*)(?P<attrs>({ATTRIBUTE})*)"

# ## The `Selector` class

# This class encapsulates a single CSS selector as defined by the
# language recognized by our `SELECTOR` regex.
# A selector is just a collection of tag, id, classes, states, attributes, and a few
# fluent methods to easily compose complex selector (like selectors with the `>` operator).

# The two main functionalities in `Selector` are the [`css`](#selectorcss)
# and the [`parse`](#selectorparse) methods to convert back and from CSS-style selector strings.


class Selector:
    def __init__(
        self,
        tag: str = None,
        id: str = None,
        classes: str = (),
        states: str = (),
        *,
        parent: Selector = None,
        **attrs: Dict[str, str],
    ) -> None:
        self._id = id
        self._tag = tag
        self._classes = tuple(classes)
        self._states = tuple(states)
        self._attrs = dict(**attrs)
        self._parent = parent

    # #### `Selector.css`

    def css(self) -> str:
        """Returns a CSS-style string for this selector.

        **Examples**:

        ```python
        >>> Selector(tag='div', id='main', classes=['bar', 'foo']).css()
        'div#main.bar.foo'

        >>> Selector(states=['hover', 'active']).css()
        ':hover:active'

        ```

        Also works with children selector:

        ```python
        >>> Selector('ul', id='main').children('li', nth=2).css()
        'ul#main>li:nth-child(2)'

        ```

        And with attributes:

        ```python
        >>> Selector(classes=['component'], state='on').css()
        '.component[state=on]'

        ```

        """
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

        for state in self._states:
            parts.append(f":{state}")

        for attr, value in self._attrs.items():
            parts.append(f"[{str(attr)}={str(value)}]")

        return "".join(parts)

    # #### `Selector.parse`

    @classmethod
    def parse(cls, selector: str = "*", *, parent: Selector = None) -> Selector:
        """Parses a CSS-style selector string.

        **Parameters:**

        - `selector`: The CSS selector.
        - `parent`: Optional. The selector from which this was derived.

        **Examples:**

        ```python
        >>> Selector.parse('.btn:active')
        Selector(classes=('btn',), states=('active',))

        >>> Selector.parse('div#main.bar.foo:hover:active')
        Selector(tag='div', id='main', classes=('bar', 'foo'), states=('hover', 'active'))

        >>> Selector.parse('.component[state=on]')
        Selector(classes=('component',), attrs={'state': 'on'})

        ```
        """
        match = re.fullmatch(SELECTOR, selector)

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

        states = match.group("states")

        if states:
            states = states.split(":")[1:]
        else:
            states = []

        attrs = {}
        attrs_match = match.group("attrs")

        if attrs_match:
            attr_parts = attrs_match.split("][")

            for part in attr_parts:
                key, value = part.split("=")
                key = key.lstrip("[")
                value = value.rstrip("]")
                attrs[key] = value

        return Selector(tag, id, classes, states, parent=parent, **attrs)

    # #### `Selector.on`

    def on(self, *states: str, **attrs) -> Selector:
        """Returns a new selector with a state and/or a set of attributes.

        **Parameters:**

        - `states`: Optional, a sequence of states like `'hover', 'active'`.
        - `attrs`: Key-value string pairs for attributes like `state='on'`.

        **Examples:**

        ```python
        >>> Selector.parse('.btn').on('hover', 'active')
        Selector(classes=('btn',), states=('hover', 'active'))

        >>> Selector.parse('.btn').on('hover', state='on')
        Selector(classes=('btn',), states=('hover',), attrs={'state': 'on'})

        ```
        """
        return Selector(
            self._tag,
            self._id,
            self._classes,
            list(self._states) + list(states),
            parent=self._parent,
            **dict(self._attrs, **attrs),
        )

    # #### `Selector.children`

    def children(self, selector: str, *, nth: int = None) -> Selector:
        s = Selector.parse(selector, parent=self)

        if nth is not None:
            s = s.on(f"nth-child({nth})")

        return s

    # #### `Selector.markup`

    def markup(self) -> str:
        parts = []

        if self._id:
            parts.append(f'id="{self._id}"')

        if self._classes:
            classes = " ".join(self._classes)
            parts.append(f'class="{classes}"')

        return " ".join(parts)

    # #### `Selector.__str__`

    def __str__(self) -> str:
        return self.css()

    # #### `Selector.__repr__`

    def __repr__(self) -> str:
        parts = []

        if self._tag:
            parts.append("tag=" + repr(self._tag))

        if self._id:
            parts.append("id=" + repr(self._id))

        if self._classes:
            parts.append("classes=" + repr(self._classes))

        if self._states:
            parts.append("states=" + repr(self._states))

        if self._attrs:
            parts.append("attrs=" + repr(self._attrs))

        body = ", ".join(parts)

        return f"Selector({body})"
