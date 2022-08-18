from violetear import StyleSheet, Style, Color, Unit, rem

base_style = Style().color(Color.gray(0.3))
sheet = StyleSheet(normalize=True, base=base_style)

sheet.select("body").width(0.8, max=768).margin("auto", top=50)

for i, size in enumerate(Unit.scale(rem, 1, 2.25, 3)):
    sheet.select(f".size-{i}").font(size, weight=300)

sheet.render("styles.css")
