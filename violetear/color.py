import colorsys

from .units import Unit


class Color:
    def __init__(
        self, red: int = 0, green: int = 0, blue: int = 0, alpha: float = 1.0
    ) -> None:
        self.r = red
        self.g = green
        self.b = blue
        self.a = 1.0 if alpha is None else alpha

    def __str__(self):
        return f"rgba({self.r},{self.g},{self.b},{self.a})"

    @classmethod
    def from_hsv(
        cls, hue: float, saturation: float, value: float, alpha: float = 1.0
    ) -> "Color":
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        return Color(int(r * 255), int(g * 255), int(b * 255), alpha)

    def to_hsv(self):
        return colorsys.rgb_to_hsv(self.r / 255, self.g / 255, self.b / 255)

    @classmethod
    def from_hls(
        cls, hue: float, lightness: float, saturation: float, alpha: float = 1.0
    ) -> "Color":
        r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
        return Color(int(r * 255), int(g * 255), int(b * 255), alpha)

    def to_hls(self):
        return colorsys.rgb_to_hls(self.r / 255, self.g / 255, self.b / 255)

    def to_rgb(self):
        return self.r, self.g, self.b

    def saturated(self, saturation: float) -> "Color":
        h, _, v = self.to_hsv()
        return Color.from_hsv(h, saturation, v, self.a)

    def lit(self, lightness: float) -> "Color":
        h, _, s = self.to_hls()
        return Color.from_hls(h, lightness, s, self.a)

    @classmethod
    def red(cls, lightness: float = 1.0):
        return Color(255, 0, 0, 1).lit(lightness)

    @classmethod
    def green(cls, lightness: float = 1.0):
        return Color(0, 255, 0, 1).lit(lightness)

    @classmethod
    def blue(cls, lightness: float = 1.0):
        return Color(0, 0, 255, 1).lit(lightness)

    @classmethod
    def gray(cls, lightness: float = 1.0):
        return Color(255, 255, 255, 1).lit(lightness)

    @staticmethod
    def palette(start: "Color", end: "Color", steps: int, space="hls"):
        from_space = getattr(Color, f"from_{space}")
        to_space = getattr(Color, f"to_{space}")

        start_values = to_space(start)
        end_values = to_space(end)
        step_values = [
            list(Unit.scale(float, s, e, steps))
            for s, e in zip(start_values, end_values)
        ]

        for tuple in zip(*step_values):
            yield from_space(*tuple)
