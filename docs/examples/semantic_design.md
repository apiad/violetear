# Creating a semantic design system

In this example we will create a simple semantic design system with
classes for sizes (`sm`, `md`, ...) and roles (`primary`, `error`, ...).
Using these clases we will style text and buttons.

You can see the end result [here](./semantic-design.html),
the corresponding CSS file [here](./semantic-design.css),
and the Python script [here](./semantic_design.py).



```python linenums="8" title="semantic_design.py"
from violetear import StyleSheet
from violetear.color import Colors
from violetear.units import Unit, rem
```

As usual, we start with an empty stylesheet (except for normalization styles).



```python linenums="12" hl_lines="1" title="semantic_design.py"
sheet = StyleSheet(normalize=True)  
sheet.select("body").width(max=768).margin("auto")  
```

Then, we style our `body` with a proper size and margin to get some space.
This has nothing to do with our design system, it's just to make the example page look better.



```python linenums="12" hl_lines="2" title="semantic_design.py"
sheet = StyleSheet(normalize=True)  
sheet.select("body").width(max=768).margin("auto")  
```


## Basic styles

If you look at the HTML document, you'll notice we have some basic typography that we want
to style with class `text`, as well as some buttons with class `btn`.

```html linenums="9" title="semantic-design.html"
...
<body>
    <div>
        <h1>Typography</h1>

        <h2>Text sizes</h2>
        <div class="text xs normal">Tiny text</div>
        <div class="text sm normal">Small text</div>
        <div class="text md normal">Medium text</div>
        <div class="text lg normal">Large text</div>
        <div class="text xl normal">Huge text</div>
...
```

```html linenums="30"
...
        <h2>Button sizes</h2>
        <button class="btn xs normal">Tiny</button>
        <button class="btn sm normal">Small</button>
        <button class="btn md normal">Medium</button>
        <button class="btn lg normal">Large</button>
        <button class="btn xl normal">Huge</button>
...
```

We will begin by styling our `text` class with slightly lighter gray color.



```python linenums="31" hl_lines="1" title="semantic_design.py"
base_text = sheet.select(".text").color(Colors.Black.lit(0.2))  

base_btn = (
    sheet.select(".btn")
    .rule("cursor", "pointer")  
    .rounded()  
    .shadow(Colors.Black.transparent(0.2), x=2, y=2, blur=4)  
    .transition(duration=50)  
)
```

And our `btn` class with a basic button-like style including a pointer cursor,
rounded corners, and a light shadow.



```python linenums="31" hl_lines="5 6 7" title="semantic_design.py"
base_text = sheet.select(".text").color(Colors.Black.lit(0.2))  

base_btn = (
    sheet.select(".btn")
    .rule("cursor", "pointer")  
    .rounded()  
    .shadow(Colors.Black.transparent(0.2), x=2, y=2, blur=4)  
    .transition(duration=50)  
)
```


With `transition` we also activate animated transitions with a very short
duration (`50ms`). Check the [animations](../animations/) example for more details on this method.



```python linenums="31" hl_lines="8" title="semantic_design.py"
base_text = sheet.select(".text").color(Colors.Black.lit(0.2))  

base_btn = (
    sheet.select(".btn")
    .rule("cursor", "pointer")  
    .rounded()  
    .shadow(Colors.Black.transparent(0.2), x=2, y=2, blur=4)  
    .transition(duration=50)  
)
```


## Creating the size classes

Semantic design systems often have classes like `sm`, `lg`, etc., that represent different sizes
for the same type of element.
In our system, we want to style things like `.text.sm` and `.btn.lg`, so we will define these size
classes for both `.text` and `.btn`.

First, we will create a scale of `rem` 5 values.



```python linenums="52" title="semantic_design.py"
font_sizes = Unit.scale(rem, 0.8, 2.2, 5)
```

Next, we will zip the class names with the corresponding sizes to create all size styles
at once:



```python linenums="55" hl_lines="1" title="semantic_design.py"
for cls, font in zip(["xs", "sm", "md", "lg", "xl"], font_sizes):  
    text_size = sheet.select(f".text.{cls}").font(size=font)  
    pd = font / 4  
    btn_size = (
        sheet.select(f".btn.{cls}")
        .font(size=font)  
        .padding(left=pd * 2, top=pd, bottom=pd, right=pd * 2)  
    )
```

For `.text` we just need to define the font size using the appropiate size.
For example, selector `.text.xs` will have a font size of `0.8rem` and selector
`.text.xl` will have a font size of `2.2rem`.



```python linenums="55" hl_lines="2" title="semantic_design.py"
for cls, font in zip(["xs", "sm", "md", "lg", "xl"], font_sizes):  
    text_size = sheet.select(f".text.{cls}").font(size=font)  
    pd = font / 4  
    btn_size = (
        sheet.select(f".btn.{cls}")
        .font(size=font)  
        .padding(left=pd * 2, top=pd, bottom=pd, right=pd * 2)  
    )
```


For buttons, we will define a suitable padding value derived from the current size
and set both the font size and the padding.



```python linenums="55" hl_lines="3 6 7" title="semantic_design.py"
for cls, font in zip(["xs", "sm", "md", "lg", "xl"], font_sizes):  
    text_size = sheet.select(f".text.{cls}").font(size=font)  
    pd = font / 4  
    btn_size = (
        sheet.select(f".btn.{cls}")
        .font(size=font)  
        .padding(left=pd * 2, top=pd, bottom=pd, right=pd * 2)  
    )
```


## Creating the color styles

For color styles, we will define a custom palette of hand-picked colors.
Some are darker, some are brighter.
These will be the background colors of our semantic button classes.



```python linenums="74" title="semantic_design.py"
colors = [
    Colors.White.lit(0.9),
    Colors.Blue.lit(0.3),
    Colors.Green.lit(0.3),
    Colors.Orange.lit(0.6),
    Colors.Red.lit(0.3),
    Colors.Cyan.lit(0.4),
]
```

With these definitions we can create all our color styles in single loop.



```python linenums="83" title="semantic_design.py"
for cls, color in zip("normal primary success warning error info".split(), colors):
```

First, the text style will simply define the color for each `.text.<cls>` selector.
For example, `.text.primary` will get a dark blue color.

Since some colors are darker and some are brighter, and for text we need
a consistent level of contrast, we will get the `0.2`-lightness version of
each color:



```python linenums="89" title="semantic_design.py"
    text_style = sheet.select(f".text.{cls}").color(color.lit(0.2))
```

Now, for the buttons, we need to define the text color in a way that contrasts
with the background color. We use the `Color.lightness` property to select
between a darker and a lighter version of the background color.



```python linenums="93" title="semantic_design.py"
    if color.lightness < 0.4:
        text_color = color.lit(0.9)
        accent_color = Colors.White
    else:
        text_color = color.lit(0.1)
        accent_color = Colors.Black
```

Now it's finally time to style the buttons.
We will need to style also the hover and active behaviours.

First, the raw button style, which simply assigns the corresponding
foreground and background colors to each semantic class.



```python linenums="103" hl_lines="1" title="semantic_design.py"
    btn_style = sheet.select(f".btn.{cls}").background(color).color(text_color)  
    hover = (
        btn_style.on("hover")
        .background(color.lighter(0.2))  
        .color(accent_color)  
    )
    active = (
        btn_style.on("active")
        .color(accent_color)  
        .background(color.darker(0.1))  
        .shadow(color.lit(0.2).transparent(0.2), x=0, y=0, blur=2, spread=1)  
    )
```

The on-hover style will change to a slightly lighter version of the background color,
and choose either pure black or white for the foreground text color.
This will have the nice effect of lighting up or button a bit.



```python linenums="103" hl_lines="4 5" title="semantic_design.py"
    btn_style = sheet.select(f".btn.{cls}").background(color).color(text_color)  
    hover = (
        btn_style.on("hover")
        .background(color.lighter(0.2))  
        .color(accent_color)  
    )
    active = (
        btn_style.on("active")
        .color(accent_color)  
        .background(color.darker(0.1))  
        .shadow(color.lit(0.2).transparent(0.2), x=0, y=0, blur=2, spread=1)  
    )
```


And finally, the active style will darken the background a bit, and move the shadow
so that it sits directly under the button, given the impression that it was indeed pressed:



```python linenums="103" hl_lines="9 10 11" title="semantic_design.py"
    btn_style = sheet.select(f".btn.{cls}").background(color).color(text_color)  
    hover = (
        btn_style.on("hover")
        .background(color.lighter(0.2))  
        .color(accent_color)  
    )
    active = (
        btn_style.on("active")
        .color(accent_color)  
        .background(color.darker(0.1))  
        .shadow(color.lit(0.2).transparent(0.2), x=0, y=0, blur=2, spread=1)  
    )
```


