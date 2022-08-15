class Color:
    def __init__(self, red:int=0, green:int=0, blue:int=0, alpha:float=1.0) -> None:
        self.red = red
        self.green = green
        self.blue = blue
        self.alpha = alpha

    def __str__(self):
        return f"rgba({self.red},{self.green},{self.blue},{self.alpha})"

    @classmethod
    def from_name(cls, name:str) -> "Color":
        return COLORS[name]


COLORS = dict(
    red=Color(255,0,0),
    green=Color(0,255,0),
    blue=Color(0,0,255),
)
