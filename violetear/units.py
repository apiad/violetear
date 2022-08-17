class Unit:
    def __init__(self, value, unit) -> None:
        self.value = value
        self.unit = unit

    def __str__(self):
        return f"{self.value}{self.unit}"

    @staticmethod
    def infer(x):
        if isinstance(x, int):
            return px(x)
        elif isinstance(x, float):
            return pc(x)

        return x


def pt(x: int):
    return Unit(x, "pt")


def em(x: int):
    return Unit(x, "em")


def px(x: int):
    return Unit(x, "px")


def pc(x: float):
    return Unit(round(x*100,2), "%")
