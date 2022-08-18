def px(x: int):
    return Unit(x, "px")


def pt(x: float):
    return Unit(x, "pt")


def em(x: float):
    return Unit(x, "em")


def rem(x: float):
    return Unit(x, "rem")


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
