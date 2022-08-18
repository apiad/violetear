from violetear import StyleSheet, Style, Color, Unit, rem

base_style = Style().color(Color.gray(0.3))
sheet = StyleSheet(normalize=True, base=base_style)

sheet.select("body").width(0.8, max=768).margin("auto", top=50)

for i, size in enumerate(Unit.scale(rem, 1, 2.25, 3)):
    sheet.select(f".size-{i}").font(size, weight=300)

palette = Color.palette(Color.red(0.3), Color.blue(0.7), 10)
root = sheet.select("#color-palette").flexbox()

for i, color in enumerate(palette):
    root.children("div", nth=i + 1).width(1.0).height(10).margin(0.1).background(
        color
    ).rounded()

gallery = sheet.select("#gallery").flexbox(wrap=True, justify="space-around")
gallery.children("div").flex(1).width(min=100, max=200).height(100).background(
    Color.gray(0.9)
).margin(0.1)

with sheet.media(max_width=600):
    sheet.select("body").width(1.0).padding(left=10, right=10)
    sheet.redefine(root).flexbox("column").children("div").width(max=200)
    sheet.redefine(gallery).hidden()

sheet.render("styles.css")
