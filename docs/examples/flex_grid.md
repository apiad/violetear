

```python linenums="1" title="flex_grid.py"
from violetear import StyleSheet
from violetear.color import gray

sheet = StyleSheet(normalize=True)

sheet.select(".main").padding(50)
sheet.select(".container").background(gray(0.9)).padding(10).margin(bottom=10)
sheet.select(".col").background(gray(0.95)).border(0.1, gray(1)).height(100)

sheet.select(".row").flexbox(wrap=True)

for size in range(1, 13):
    sheet.select(f".span-{size}").width(size / 12)

if __name__ == "__main__":
    sheet.render("flex-grid-1.css")
```

End of first section

<a name="ref:make_grid_styles"></a>

```python linenums="18" title="flex_grid.py"
sheet = StyleSheet(normalize=True)

sheet.select(".main").padding(50)
sheet.select(".container").background(gray(0.9)).padding(10).margin(bottom=10)
sheet.select(".col").background(gray(0.95)).border(0.1, gray(1)).height(100)

sheet.select(".row").flexbox(wrap=True)


def make_grid_styles(columns):
    for size in range(1, columns):
        sheet.select(f".span-{size}").width(size / columns)

    for size in range(columns, 13):
        sheet.select(f".span-{size}").width(1.0)


make_grid_styles(12)

with sheet.media(max_width=1600):
    make_grid_styles(8)

with sheet.media(max_width=1200):
    make_grid_styles(6)

with sheet.media(max_width=800):
    make_grid_styles(4)

with sheet.media(max_width=600):
    make_grid_styles(1)

if __name__ == "__main__":
    sheet.render("flex-grid-2.css")
```

End of second section

<a name="ref:make_grid_styles"></a>

```python linenums="52" title="flex_grid.py"
sheet = StyleSheet(normalize=True)

sheet.select(".main").padding(50)
sheet.select(".container").background(gray(0.9)).padding(10).margin(bottom=10)
sheet.select(".col").background(gray(0.95)).border(0.1, gray(1)).height(100)

sheet.select(".row").flexbox(wrap=True)


def make_grid_styles(columns, custom=None):
    for size in range(1, columns):
        sheet.select(f".span-{size}").width(size / columns)

    for size in range(columns, 13):
        sheet.select(f".span-{size}").width(1.0)

    if custom:
        for size in range(1, columns + 1):
            sheet.select(f".{custom}-{size}").width(size / columns)


make_grid_styles(12)

with sheet.media(max_width=1600):
    make_grid_styles(8, "lg")

with sheet.media(max_width=1200):
    make_grid_styles(6, "md")

with sheet.media(max_width=800):
    make_grid_styles(4, "sm")

with sheet.media(max_width=600):
    make_grid_styles(1)

if __name__ == "__main__":
    sheet.render("flex-grid-3.css")
```

End of third section

<a name="ref:make_grid_styles"></a>

```python linenums="90" title="flex_grid.py"
sheet = StyleSheet(normalize=True)

sheet.select(".main").padding(50)
sheet.select(".container").background(gray(0.9)).padding(10).margin(bottom=10)
sheet.select(".col").background(gray(0.95)).border(0.1, gray(1)).height(100)

sheet.select(".row").flexbox(wrap=True)


def make_grid_styles(columns, custom=None):
    for size in range(1, columns):
        sheet.select(f".span-{size}").width(size / columns)

    for size in range(columns, 13):
        sheet.select(f".span-{size}").width(1.0)

    if custom:
        for size in range(1, columns + 1):
            sheet.select(f".{custom}-{size}").width(size / columns)


make_grid_styles(12)
sheet.select(".fixed").width(max=1500).margin("auto")

with sheet.media(max_width=1600):
    make_grid_styles(8, "lg")
    sheet.select(".fixed").width(max=1100)

with sheet.media(max_width=1200):
    make_grid_styles(6, "md")
    sheet.select(".fixed").width(max=700)

with sheet.media(max_width=800):
    make_grid_styles(4, "sm")
    sheet.select(".fixed").width(max=500)

with sheet.media(max_width=600):
    make_grid_styles(1)

if __name__ == "__main__":
    sheet.render("flex-grid.css")
```

End of tutorial

