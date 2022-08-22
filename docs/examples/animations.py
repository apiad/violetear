from violetear import StyleSheet
from violetear.color import gray, red

sheet = StyleSheet(normalize=True)

sheet.select(".menu").flexbox(gap=10).padding(10)
items = (
    sheet.select(".menu-item")
    .padding(5)
    .border(0.1, gray(0.5))
    .background(gray(0.7))
    .text(decoration=False)
    .font(weight=600)
)

items.transition("background-color").on("hover").background(gray(0.9))
items.transition("color", 300).on("hover").color(red(0.5))

items.transition(
    property="transform",
    duration=150,
    timing="ease-in-out",
    delay=150,
).on("hover").scale(1.1).translate(y=5)

if __name__ == "__main__":
    sheet.render("animations.css")
