import colorsys


class Color:
    def __init__(
        self, red: int = 0, green: int = 0, blue: int = 0, alpha: float = 1.0
    ) -> None:
        self.red = red
        self.green = green
        self.blue = blue
        self.alpha = 1.0 if alpha is None else alpha

    def __str__(self):
        return f"rgba({self.red},{self.green},{self.blue},{self.alpha})"

    @classmethod
    def from_hsv(
        cls, hue: float, saturation: float, value: float, alpha: float = 1.0
    ) -> "Color":
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        return Color(int(r * 255), int(g * 255), int(b * 255), alpha)

    def to_hsv(self):
        return colorsys.rgb_to_hsv(self.red / 255, self.green / 255, self.blue / 255)

    def saturated(self, saturation: float) -> "Color":
        h, _, v = self.to_hsv()
        return Color.from_hsv(h, saturation, v, self.alpha)

    def lit(self, value: float) -> "Color":
        h, s, _ = self.to_hsv()
        return Color.from_hsv(h, s, value, self.alpha)

    @classmethod
    def red(cls, value: float = 1.0):
        return Color(255, 0, 0, 1).lit(value)

    @classmethod
    def green(cls, value: float = 1.0):
        return Color(0, 255, 0, 1).lit(value)

    @classmethod
    def blue(cls, value: float = 1.0):
        return Color(0, 0, 255, 1).lit(value)

    @classmethod
    def gray(cls, value: float = 1.0):
        return Color(255, 255, 255, 1).lit(value)
