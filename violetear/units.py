from typing import List, Union


def px(x: int):
    return Unit(x, "px")


def pt(x: float):
    return Unit(x, "pt")


def em(x: float):
    return Unit(x, "em")


def rem(x: float):
    return Unit(x, "rem")


def fr(x: float):
    return Unit(x, "fr")


def pc(x: float):
    return Unit(round(x * 100, 2), "%")


class Unit:
    def __init__(self, value, unit) -> None:
        self.value = value
        self.unit = unit

    def __str__(self):
        return f"{self.value}{self.unit}"

    @staticmethod
    def infer(x, on_float=rem, on_int=px):
        if isinstance(x, int):
            return on_int(x)
        elif isinstance(x, float):
            return on_float(x)

        return x

    @staticmethod
    def scale(unit, min_value, max_value, steps):
        current = min_value
        delta = (max_value - min_value) / (steps - 1)

        for _ in range(steps):
            yield unit(current)
            current += delta


GridTemplate = Union[Unit, "repeat", "minmax"]
GridSize = Union[Unit, "minmax"]


class repeat:
    def __init__(self, factor, *template: List[GridTemplate]) -> None:
        self.factor = factor
        self.template = template

    def __str__(self) -> str:
        template = " ".join(str(Unit.infer(u, on_float=fr)) for u in self.template)
        return f"repeat({self.factor}, {template})"


class minmax:
    def __init__(self, min, max) -> None:
        self.min = min
        self.max = max

    def __str__(self) -> str:
        return f"minmax({self.min}, {self.max})"
