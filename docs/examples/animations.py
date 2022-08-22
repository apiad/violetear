from violetear import StyleSheet
from violetear.color import blue, gray, green, red
from violetear.animation import Animation
from violetear.style import Style
from violetear.units import px, sec

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

sheet.select(".marquee").height(500).rules(overflow="hidden").padding(20)
text = sheet.select("p").font(size=22, weight=100).relative()

animation = (
    Animation("text-up")
    .start(top=px(500))
    .at(0.25, Style().color(green(0.3)))
    .at(0.50, Style().color(blue(0.3)).font(weight=900))
    .at(0.75, Style().color(red(0.3)))
    .end(top=px(-500))
)

text.animation(animation, duration=sec(10), iterations="infinite")

if __name__ == "__main__":
    sheet.render("animations.css")
