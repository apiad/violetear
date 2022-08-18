from violetear import StyleSheet, Style, Color

sheet = StyleSheet(normalize=True, base=Style().color(Color.gray(0.3)))

sheet.select("body").width(0.8, max=768).margin("auto", top=50)

sheet.render("styles.css")
