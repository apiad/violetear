# Making a fluid grid with flexbox

In this example we'll build a fluid grid system (a la old-fashion Bootstrap) using flexbox. You can see the HTML result [here](flex-grid.html) and the final CSS file [here](flex-grid.css). Try resizing the browser window so you can get a feel for the kind of behaviour we want to replicate.

Ready? Let's begin!

## Basic grid

We will start by coding a basic flexbox 12-column grid system.
The concepts we want to express are:

- `.container` is the main grid system.
- `.row` is a single row.
- `.col` is a single cell inside a row.
- `span-1` ... `.span-12` is the size of each cell.

This is our test markup (you can check it [here](flex-grid-1.html))

```html title="flex-grid.html"
<!-- The usual stuff (1) -->
<body class="main">
    <div class="container">
        .container
        <div class="row">
            <div class="col span-12">.span-12</div>
        </div>
        <div class="row">
            <div class="col span-1">.span-1</div>
            <div class="col span-1">.span-1</div>
            <div class="col span-4">.span-4</div>
            <div class="col span-6">.span-6</div>
        </div>
    </div>

    <div class="container fixed">
        .container .fixed
        <div class="row">
            <div class="col span-2">.span-2</div>
            <div class="col span-3">.span-3</div>
            <div class="col span-3">.span-3</div>
            <div class="col span-4">.span-4</div>
        </div>
    </div>
</body>
```

1. Include here all the usual markup. Don't forget to link your CSS!

As usual, we start by creating an stylesheet empty:

```python title="flex-grid.py" hl_lines="4"
from violetear import StyleSheet
from violetear.color import gray

sheet = StyleSheet(normalize=True)

sheet.select(".main").padding(50)
sheet.select(".container").background(gray(0.9)).padding(10).margin(bottom=10)
sheet.select(".col").background(gray(0.95)).border(0.1, gray(1)).height(100)

sheet.select(".row").flexbox(wrap=True)

for size in range(1, 13):
    sheet.select(f".span-{size}").width(size / 12)

sheet.render("flex-grid.css")
```

Next we will add some basic styling to make some space and to render our containers and cols visible:

```python title="flex-grid.py" hl_lines="6 7 8"
from violetear import StyleSheet
from violetear.color import gray

sheet = StyleSheet(normalize=True)

sheet.select(".main").padding(50)
sheet.select(".container").background(gray(0.9)).padding(10).margin(bottom=10)
sheet.select(".col").background(gray(0.95)).border(0.1, gray(1)).height(100)

sheet.select(".row").flexbox(wrap=True)

for size in range(1, 13):
    sheet.select(f".span-{size}").width(size / 12)

sheet.render("flex-grid.css")
```

Next we make each `.row` flexible using `.flexbox` with `wrap=True`. This immediately makes all columns to align horizontally.

```python title="flex-grid.py" hl_lines="10"
from violetear import StyleSheet
from violetear.color import gray

sheet = StyleSheet(normalize=True)

sheet.select(".main").padding(50)
sheet.select(".container").background(gray(0.9)).padding(10).margin(bottom=10)
sheet.select(".col").background(gray(0.95)).border(0.1, gray(1)).height(100)

sheet.select(".row").flexbox(wrap=True)

for size in range(1, 13):
    sheet.select(f".span-{size}").width(size / 12)

sheet.render("flex-grid.css")
```

And finally, we will create all our `.span-x` styles in single sweep of a hand, simply by setting their width to the corresponding fraction of the grid:

```python title="flex-grid.py" hl_lines="12 13"
from violetear import StyleSheet
from violetear.color import gray

sheet = StyleSheet(normalize=True)

sheet.select(".main").padding(50)
sheet.select(".container").background(gray(0.9)).padding(10).margin(bottom=10)
sheet.select(".col").background(gray(0.95)).border(0.1, gray(1)).height(100)

sheet.select(".row").flexbox(wrap=True)

for size in range(1, 13):
    sheet.select(f".span-{size}").width(size / 12)

sheet.render("flex-grid.css")
```

And that's it. Just like that, we have a flexible grid system that expands and stretches as necessary. Call it a day? No way! We still haven't even scratched the surface of what we can achieve.

## Grid breakpoints

The first problem we have with our current layout is that when the screen becomes smaller, the columns keep stretching and stretching until they are barely visible. So what we need to do now is to add breakpoints to make smaller grids, with less columns.

For example, when we hit 1600px we switch to an 8-column grid, when we hit 1200px we switched to 6-columns, and so on until we have a single column design.

To achieve this we need media queries to redefine the size of our `.span-x` classes at each breakpoint. Let's say we have 8 columns at breakpoint 1600px. Then we will make `span-1` to `span-8` to cover the entire range, and `span-9` and upwards to become `100%` wide. This way, when the screen shrinks below 1600px, the columns will snap into their new widths, for example, `span-4` goes from `0.33%` (1/12) to `0.50%` (1/8). Sounds reasonable?

Hands on! To code this in the DRYest possible way, we'll make a function that receives the number of columns we want and defines all the styles correspondingly. Something like this:

```python
def make_grid_styles(columns):
    # For span-1 to span-{columns}
    for size in range(1, columns):
        sheet.select(f".span-{size}").width(size / columns)

    # For span-{columns} and upwards
    for size in range(columns, 13):
        sheet.select(f".span-{size}").width(1.0)
```

Now we just need to call this function at different breakpoints with the right column count:

```python title="flex_grid.py" hl_lines="21 23 24 26 27 29 30 32 33"
from violetear import StyleSheet
from violetear.color import gray

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

sheet.render("flex-grid.css")
```

Go ahead and play with the [HTML file](flex-grid-2.html) we have so far and reduce the browser screen to see how columns will snap into an 8-grid, 6-grid, 4-grid, and then a single column at convenient breakpoints. Beautifull, isn't it? Well..., not perfect, because now we have some holes when columns doesn't fit in a single row and they don't add up to full size. We will fix this next.

## Conditional sizes

What we want now is to use additional classes in `.col` element to redefine what happens at different breakpoints. For example, say we have an item with `.span-6`. That element fits the `50%` of the parent container in a 12-grid system, but when we jump to an 8-grid system, it takes a rather ugly `.75%`. We can isteand give it a class `lg-8` which says in the `large` layout (say 1200 to 1600px) this item should instead span 8 columns.

Extending this idea into all grid breakpoints, what we want now is to have `sm-1` to `sm-4` for small screens (400px to 800px), `md-1` to `md-6` for medium screens (800px to 1200px), `lg-1` to `lg-8` for large screens (1200px to 1600px) and our 12 original `span-x` for the general size (over 1600px). With these classes, we could mark our HTML in the following way:

```html title="flex-grid.html"
<body class="main">
    <div class="container">
        .container
        <div class="row">
            <div class="col span-12">.span-12</div>
        </div>
        <div class="row">
            <div class="col span-1 sm-2">.span-1 .sm-2</div>
            <div class="col span-1 sm-2">.span-1 .sm-2</div>
            <div class="col span-4 lg-6">.span-4 .lg-6</div>
            <div class="col span-6 lg-8">.span-6 .lg-8</div>
        </div>
    </div>

    <div class="container">
        .container
        <div class="row">
            <div class="col span-2 lg-1 md-2 sm-4">.span-2 .lg-1 .md-2 .sm-4</div>
            <div class="col span-3 lg-2 md-4 sm-4">.span-3 .lg-2 .md-4 .sm-4</div>
            <div class="col span-3 lg-2 md-2 sm-4">.span-3 .lg-2 .md-2 .sm-4</div>
            <div class="col span-4 lg-3 md-4">.span-4 .lg-3 .md-4</div>
        </div>
    </div>
</body>
```

The key idea with these conditional classes is that they only apply within a certain media query.
For example, `sm-*` only applies when the screen is smaller than 800px.
Hence, when you style your code this way, taking advantage of CSS scoping rules, first the `span-*` class will be evaluated, and you element will get the appropriate width according to the browser width. However, then the corresponding `lg-*` or `md-*` or `sm-*` will kick (if used) and override that width.

For example, say you have a `.span-4.lg-6`. This means that on extra large screens (above 1600px), this element will have 4/12 = 33.33% percent width.
However, when the screen becomes 1600px or smaller, it should snap into 4/8 = 50% width, but instead it will snap to 6/8 = 75% width.

This sounds pretty complex but in reality it only requires a few tweaks to our code.
First, we will update our `make_grid_styles` method to accept an additional `custom` parameter which we will use to define a new set of styles.
For example, when `custom="lg"`, we will create all the corresponding `lg-1` to `lg-8` classes with the right width:

```python title="flex-grid.py" hl_lines="10 17 18 19"
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

sheet.render("flex-grid.css")
```

Finally, we just need to update our calls to `make_grid_styles` with the corresponding class prefixes `lg`, `md` and `sm`.
Go ahead and play with the [HTML file](flex-grid-3.html) we have right now to see how the elements now snap to their desired size leaving no gaps.

```python title="flex-grid.py" hl_lines="25 28 31"
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

sheet.render("flex-grid.css")
```

## Making a fixed grid

Finally, we will add a `fixed` class to `container`s when we want them to have a fixed size instead of flowing with the browser width. This is by far the simplest change, we just to define `.fixed` conveniently at all screen sizes, taking into account to substract the padding from the `.main` element:

```python title="flex_grid.py" hl_lines="4 8 12 16"
# ...

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

# ...
```

And now we're done. Check the [final HTML file](flex-grid.html) to see how the lower grid remains fixed while the upper one flows. Beautiful!

We just created a fully fledged grid system with over 80 styles spanning four different screen sizes in little less than 30 lines of Python code!

## Using the preset `FlexGrid`

Flexible grids are everywhere, and since it is so easy to create one with `violetear`, it shouldn't come as a surprise that we already ship a preset flexible grid system that you can fully customize.

A preset in `violetear` is just a class that extends `StyleSheet` and pre-generates a bunch of styles all at once given a few parameters. They are all located in the `violetear.presets` namespace. The one we want now is called `FlexGrid` and it can be configured to mimic what we just coded pretty easily:

```python
from violetear import StyleSheet
from violetear.presets import FlexGrid

sheet = StyleSheet(normalize=True).extend(FlexGrid(
    columns=12,
    breakpoints=dict(
        lg=(1600, 8),
        md=(1200, 6),
        sm=(800, 4),
        xs=(400, 1)
    )
))

# ... rest of your styles
```

The method `StyleSheet.extend(...)` receives another stylesheet and copies all its styles. A preset, like `FlexGrid`, is really just a class that inherits from `StyleSheet` and creates a lot of predefined styles in its constructor. The `FlexGrid` class generates styles just like the ones we designed here, with a base number of columns, and a set of optional breakpoints. It also allows customizing all class names, but by default it uses just the ones we defined in this example.

??? note "To be honest..."

    To be honest, the `FlexGrid` preset doesn't include the `.fixed` class (although it might in the future), and of course our first couple of aesthetic styles to make containers and cols visible won't be there either, so techincally you'd still have to add a few rules manually, but the bulk of the work is already done for you!
