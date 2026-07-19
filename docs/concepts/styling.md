# Styling

violetear's styling layer is a zero-dependency Python API for generating CSS.

## StyleSheet

```python
from violetear import StyleSheet
from violetear.color import Colors

sheet = StyleSheet()

sheet.select("body") \
    .background(Colors.AliceBlue) \
    .font(family="sans-serif", size=16) \
    .margin(0)

sheet.select(".card") \
    .background(Colors.White) \
    .padding(24) \
    .rounded(8) \
    .shadow(blur=20, color="rgba(0,0,0,0.1)")
```

## Color system

```python
from violetear.color import Colors, Color

Colors.Red          # named web color
Colors.SlateBlue    # case-insensitive
Color.from_hex("#6b21a8")
Color.from_rgb(107, 33, 168)
Color.from_hsl(270, 75, 40)
```

## Inline styles

```python
from violetear.style import Style

elem.style(Style().color(Colors.Red).font(size=14, weight="bold"))
```

## Rendering

```python
css_string = sheet.render()   # full CSS text
```

Use `app.style("/path.css", sheet)` to serve a stylesheet from your App (see [App →](app.md)).
