from violetear import StyleSheet
from violetear.color import Color, Colors, red, green, blue, gray

sheet = StyleSheet(normalize=True)
sheet.select("body").width(max=768).margin("auto", top=50, bottom=50).padding(10)
sheet.select(".palette").flexbox().children("div").flex(1).height(50).margin(5)

# Basic colors
for cls, color in zip([".red", ".green", ".blue", ".gray"], [red, green, blue, gray]):
    palette = sheet.select(cls)

    for i in range(11):
        palette.children(f".shade-{i}").background(color(i / 10)).border(0.1, gray(0.4))

# Basic CSS colors
for i, color in enumerate(Colors.basic_palette()):
    sheet.select(".basic").children("div", nth=i + 1).background(color).border(0.1, gray(0.4))

# All CSS colors by palette
for palette in ['pink', 'red', 'orange', 'yellow', 'brown', 'green', 'cyan', 'blue', 'purple', 'white', 'black']:
    for i, color in enumerate(Colors.palette(palette)):
        sheet.select(f".{palette}-colors").children('div', nth=i+1).background(color).border(0.1, gray(0.4))

# Custom palette
colors = Color.palette(Colors.SandyBrown, Colors.SteelBlue, 10)

for i, color in enumerate(colors):
    sheet.select(".custom").children('div', nth=i+1).background(color).border(0.1, gray(0.4))

sheet.render("color-spaces.css")
