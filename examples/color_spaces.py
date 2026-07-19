from typing import Sequence
from violetear import StyleSheet, Style
from violetear.color import Color, Colors, red, green, blue, gray

sheet = StyleSheet(normalize=True)
sheet.select("body").width(max=768).margin("auto", top=50, bottom=50).padding(10)
sheet.select(".palette").flexbox().children("div").flex(1).height(50).margin(5)

# Basic colors
for cls, color in zip([".red", ".green", ".blue", ".gray"], [red, green, blue, gray]):
    for i in range(11):
        sheet.select(cls).children(f".shade-{i}").background(color(i / 10)).border(
            0.1, gray(0.4)
        )


def palette(style: Style, colors: Sequence[Color]) -> Style:
    for i, color in enumerate(colors):
        style.children("div", nth=i + 1).background(color).border(0.1, gray(0.4))


Style.palette = palette

# Basic CSS colors
sheet.select(".basic").palette(Colors.basic_palette())

# All CSS colors by palette
for palette in Colors.palettes():
    sheet.select(f".{palette}-colors").palette(Colors.palette(palette))

# Custom palette
sheet.select(".custom").palette(Color.palette(Colors.SandyBrown, Colors.SteelBlue, 10))

if __name__ == "__main__":
    sheet.render("color-spaces.css")
