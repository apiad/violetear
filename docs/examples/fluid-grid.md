# Making a fluid grid with flexbox

In this example we'll build a fluid grid system (a la old-fashion Bootstrap) using flexbox. You can see the HTML result [here](fluid-grid.html) and the final CSS file [here](fluid-grid.css). Try resizing the browser window so you can get a feel for the kind of behaviour we want to replicate.

Ready? Let's begin!

## Basic grid

We will start by coding a basic flexbox 12-column grid system.
The concepts we want to express are:

- `.container` is the main grid system.
- `.row` is a single row.
- `.col` is a single cell inside a row.
- `span-1` ... `.span-12` is the size of each cell.

This is our test markup (you can check it [here](fluid-grid-1.html))

```html title="fluid-grid.html"
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

```python title="fluid-grid.py" hl_lines="4"
from violetear import StyleSheet
from violetear.color import gray

sheet = StyleSheet(normalize=True)

sheet.select(".main").padding(50)
sheet.select(".container").background(gray(0.9)).padding(10).margin(bottom=10)
sheet.select(".col").background(gray(0.95)).border(0.1, gray(1)).height(100)

sheet.select(".row").flexbox(wrap=True)

for size in range(1, 13):
    sheet.select(f".span-{size}").width(size / 12)

sheet.render("fluid-grid.css")
```

Next we will add some basic styling to make some space and to render our containers and cols visible:

```python title="fluid-grid.py" hl_lines="6 7 8"
from violetear import StyleSheet
from violetear.color import gray

sheet = StyleSheet(normalize=True)

sheet.select(".main").padding(50)
sheet.select(".container").background(gray(0.9)).padding(10).margin(bottom=10)
sheet.select(".col").background(gray(0.95)).border(0.1, gray(1)).height(100)

sheet.select(".row").flexbox(wrap=True)

for size in range(1, 13):
    sheet.select(f".span-{size}").width(size / 12)

sheet.render("fluid-grid.css")
```

Next we make each `.row` flexible using `.flexbox` with `wrap=True`. This immediately makes all columns to align horizontally.

```python title="fluid-grid.py" hl_lines="10"
from violetear import StyleSheet
from violetear.color import gray

sheet = StyleSheet(normalize=True)

sheet.select(".main").padding(50)
sheet.select(".container").background(gray(0.9)).padding(10).margin(bottom=10)
sheet.select(".col").background(gray(0.95)).border(0.1, gray(1)).height(100)

sheet.select(".row").flexbox(wrap=True)

for size in range(1, 13):
    sheet.select(f".span-{size}").width(size / 12)

sheet.render("fluid-grid.css")
```

And finally, we will create all our `.span-x` styles in single sweep of a hand, simply by setting their width to the corresponding fraction of the grid:

```python title="fluid-grid.py" hl_lines="12 13"
from violetear import StyleSheet
from violetear.color import gray

sheet = StyleSheet(normalize=True)

sheet.select(".main").padding(50)
sheet.select(".container").background(gray(0.9)).padding(10).margin(bottom=10)
sheet.select(".col").background(gray(0.95)).border(0.1, gray(1)).height(100)

sheet.select(".row").flexbox(wrap=True)

for size in range(1, 13):
    sheet.select(f".span-{size}").width(size / 12)

sheet.render("fluid-grid.css")
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

```python title="fluid_grid.py" hl_lines="21 23 24 26 27 29 30 32 33"
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

sheet.render("fluid-grid.css")
```

Go ahead and play with the [HTML file](fluid-grid-2.html) we have so far and reduce the browser screen to see how columns will snap into an 8-grid, 6-grid, 4-grid, and then a single column at convenient breakpoints. Beautifull, isn't it? Well..., not perfect, because now we have some holes when columns doesn't fit in a single row and they don't add up to full size. We will fix this next.

## Conditional sizes

What we want now is to use additional classes in `.col` element to redefine what happens at different breakpoints. For example, say we have an item with `.span-6`. That element fits the `50%` of the parent container in a 12-grid system, but when we jump to an 8-grid system, it takes a rather ugly `.75%`. We can isteand give it a class `lg-8` which says in the `large` layout (say 1200 to 1600px) this item should instead span 8 columns.

Extending this idea into all grid breakpoints, what we want now is to have `sm-1` to `sm-4` for small screens (400px to 800px), `md-1` to `md-6` for medium screens (800px to 1200px), `lg-1` to `lg-8` for large screens (1200px to 1600px) and our 12 original `span-x` for the general size (over 1600px). With these classes, we could mark our HTML in the following way:

```html title="fluid-grid.html"
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