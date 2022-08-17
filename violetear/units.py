def pt(x: int):
    return Unit(x, "pt")


def em(x: int):
    return Unit(x, "em")


def rem(x: int):
    return Unit(x, "rem")


def px(x: int):
    return Unit(x, "px")


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
