from __future__ import annotations

import textwrap
from typing import Dict

from violetear.units import Unit, pc
from violetear.style import Style


class Animation:
    def __init__(self, name: str) -> None:
        self.name = name
        self._keyframes: Dict[Unit, Style] = {}

    def at(self, percent: float, style: Style = None, **kwargs) -> Animation:
        rules = Style()

        if style is not None:
            rules.apply(style)

        if kwargs:
            rules.rules(**kwargs)

        self._keyframes[pc(percent)] = rules

        return self

    def start(self, style: Style = None, **kwargs) -> Animation:
        return self.at(0.0, style, **kwargs)

    def end(self, style: Style = None, **kwargs) -> Animation:
        return self.at(1.0, style, **kwargs)

    def css(self) -> str:
        lines = [f"@keyframes {self.name} {{"]

        for keyframe, rules in self._keyframes.items():
            lines.append(textwrap.indent(f"{keyframe} {rules.css()}\n", " " * 4))

        lines.append("}")

        return "\n".join(lines)
