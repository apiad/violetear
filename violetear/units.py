class Unit:
    def __init__(self, value, unit) -> None:
        self.value = value
        self.unit = unit

    def __str__(self):
        return f"{self.value}{self.unit}"


def pt(x: int):
    return Unit(x, "pt")


def em(x: int):
    return Unit(x, "em")
