from violetear import StyleSheet
from violetear.color import Colors
from violetear.units import Unit, rem
from violetear.presets import SemanticDesign

sheet = StyleSheet(normalize=True)

sheet.select("body").width(max=768).margin("auto")

font_sizes = Unit.scale(rem, 0.8, 2.2, 5)
padding_sizes = Unit.scale(rem, 0.4, 0.8, 5)

base_text = sheet.select(".text").color(Colors.Black.lit(0.2))

base_btn = (
    sheet.select(".btn")
    .rule("cursor", "pointer")
    .rounded()
    .shadow(Colors.Black.transparent(0.2), x=2, y=2, blur=4)
    .transition(duration=50)
)

for cls, font, pd in zip(["xs", "sm", "md", "lg", "xl"], font_sizes, padding_sizes):
    text_size = sheet.select(f".text.{cls}").font(size=font)

    btn_size = (
        sheet.select(f".btn.{cls}")
        .font(size=font)
        .padding(left=pd * 2, top=pd, bottom=pd, right=pd * 2)
    )

colors = [
    Colors.White.lit(0.9),
    Colors.Blue.lit(0.3),
    Colors.Green.lit(0.3),
    Colors.Orange.lit(0.6),
    Colors.Red.lit(0.3),
    Colors.Cyan.lit(0.4),
]

for cls, color in zip(
    ["normal", "primary", "success", "warning", "error", "info"], colors
):
    if color.lightness < 0.4:
        text_color = color.lit(0.9)
        accent_color = Colors.White
    else:
        text_color = color.lit(0.1)
        accent_color = Colors.Black

    text_style = sheet.select(f".text.{cls}").color(color.lit(0.2))

    btn_style = sheet.select(f".btn.{cls}").background(color).color(text_color)
    hover = btn_style.on("hover").background(color.lighter(0.2)).color(accent_color)
    active = (
        btn_style.on("active")
        .background(color.darker(0.1))
        .color(accent_color)
        .shadow(color.lit(0.2).transparent(0.2), x=0, y=0, blur=2, spread=1)
    )

if __name__ == "__main__":
    sheet.render("semantic-inputs.css")
