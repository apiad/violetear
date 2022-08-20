# Visualizing color spaces

In this example we'll play around with all the functionality in the [`violetear.color`](/violetear/api/violetear.color/) namespace. For this purpose we'll build several color palettes. You can check the basic markup [here](color-spaces.html) and the final CSS file [here](color-spaces.css).

We'll start with some pretty basic CSS to give some margin and padding to the document body.
We'll also write a style for `.palette` elements to make them align their children in a flexible row, because we will be using lots of palettes in this examples.

```python title="color_spaces.py"
from violetear import StyleSheet

sheet = StyleSheet(normalize=True)
sheet.select('body').width(max=768).margin('auto', top=50).padding(10)
sheet.select(".palette").flexbox().children("div").flex(1).height(50).margin(5)

# ... (1)

sheet.render("color-spaces.css")
```

1. As usual, all our rules will go in here.

## Basic colors

We'll start with the four basic colors: red, green, blue, and gray. For each of these, we have a method in `violetear.color` that let us get any point in the lightning gradient.

To illustrate this, let's create a palette for each of the basic colors. In the HTML markup you'll notice we have something like this:

```html title="color-spaces.html"
<body>
    <h1>Basic colors</h1>
    <div id="basic-colors">
        <div class="red palette">
            <div class="shade-0"></div>
            <!-- ... -->
            <div class="shade-10"></div>
        </div>
        <div class="green palette">
            <div class="shade-0"></div>
            <!-- ... -->
            <div class="shade-10"></div>
        </div>
        <div class="blue palette">
            <div class="shade-0"></div>
            <!-- ... -->
            <div class="shade-10"></div>
        </div>
        <div class="gray palette">
            <div class="shade-0"></div>
            <!-- ... -->
            <div class="shade-10"></div>
        </div>
    </div>
    <!-- ... -->
</body>
```

Thus, we will style each of those `.shade-{i}` elements according to their parent class and their shade fraction. For example, the element `.shade-4` inside the `.red` palette will be background colored with `red(0.4)`. And the best part is we'll do all of this in four lines of code (plus one import):

```python title="color_spaces.py" hl_lines="2 7 8 10 11"
from violetear import StyleSheet
from violetear.color import red, green, blue, gray

# ... (1)

# Basic colors
for cls, color in zip(['.red', '.green', '.blue', '.gray'], [red, green, blue, gray]):
    palette = sheet.select(cls)

    for i in range(11):
        palette.children(f'.shade-{i}').background(color(i/10)).border(0.1, gray())

sheet.render("color-spaces.css")
```

Voilá! Just like that we created 40 different CSS styles. If you look at the file CSS file you'll notice a bunch of rules like:

```css title="color-spaces.css"
.red>.shade-0 {
    background-color: rgba(0,0,0,1.0);
}

.red>.shade-1 {
    background-color: rgba(51,0,0,1.0);
}

.red>.shade-2 {
    background-color: rgba(102,0,0,1.0);
}

/* ... */

.red>.shade-9 {
    background-color: rgba(254,204,204,1.0);
}

.red>.shade-10 {
    background-color: rgba(255,255,255,1.0);
}

/* ... */
```

## CSS colors

If you need more colors, the `Colors` class contains definitions for all CSS colors, which can be accessed either by name or by dot notation.

As an example, let's style the 16 basic CSS colors explicitly.

```python title="color_spaces.py"
# ... (1)

basic_colors = [
    Colors.White,
    Colors.Silver,
    Colors.Gray,
    Colors.Black,
    Colors.Red,
    Colors.Maroon,
    Colors.Yellow,
    Colors.Olive,
    Colors.Lime,
    Colors.Green,
    Colors.Aqua,
    Colors.Teal,
    Colors.Blue,
    Colors.Navy,
    Colors.Fuchsia,
    Colors.Purple,
]

for i, color in enumerate(basic_colors):
    sheet.select(".basic").children('div', nth=i+1).background(color).border(0.1, gray())

# ... (2)
```

1. Rest of the script hidden for simplicity.
2. Rest of the script hidden for simplicity.

However, explicitely listing colors is so boring, that `Colors` provides several methods for enumerating common palettes. So the same can be achieved with:

```python title="color_spaces.py"
# ... (1)

for i, color in enumerate(Colors.basic_palette()):
    sheet.select(".basic").children("div", nth=i + 1).background(color).border(0.1, gray())

# ... (2)
```

1. Rest of the script hidden for simplicity.
2. Rest of the script hidden for simplicity.

Now let's do the same but with all the CSS palettes. The method `Colors.palette()` returns a palette by name. For each palette, there's also an explicit method for it. So you can either use `Colors.red_palette()` or `Colors.palette("red")`.

```python title="color_spaces.py"
# ... (1)

for palette in ['pink', 'red', 'orange', 'yellow', 'brown', 'green', 'cyan', 'blue', 'purple', 'white', 'black']:
    for i, color in enumerate(Colors.palette(palette)):
        sheet.select(f".{palette}-colors").children('div', nth=i+1).background(color).border(0.1, gray(0.4))

# ... (2)
```

1. Rest of the script hidden for simplicity.
2. Rest of the script hidden for simplicity.

But you don't have to remember the palette names, do you? Of course not, you can just as easily call `Colors.palettes()` which will return all the predefined palettes.

```python title="color_spaces.py"
# ... (1)

for palette in Colors.palettes():
    for i, color in enumerate(Colors.palette(palette)):
        sheet.select(f".{palette}-colors").children('div', nth=i+1).background(color).border(0.1, gray(0.4))

# ... (2)
```

1. Rest of the script hidden for simplicity.
2. Rest of the script hidden for simplicity.

And finally, you have the method `Colors.all()` which gives you all the pre-defined colors.

??? question "Why so many options?"
    At this point you may be asking why do we need both dot notation and dictionary notation to access names. For example, you can use:

    ```python
    color = Colors.SlateBlue
    # or
    color = Colors['SlateBlue']
    ```

    Same with palettes, you can access them by name and by dot notation.

    The reason is simple: both forms are useful, and `violetear` tries to be non-opinionated.
    When you're explicitly defining a style, writing Python code, you probably prefer the dot notation, because you'll have intellisense, code completion, documentation, etc.

    However, if you're designing a style programatically, using some sort of user input (e.g., you want the user to pick a palette in a combobox), then you'll prefer the dictionary notation. Otherwise you'd have to use lots of `getattr` (which is actually what's happening deep down).

## Custom palettes

But what if you don't want to use existing colors, but create a custom palette of your own?
In this case, the `Color` class has a lot of utilites for creating, combining, and tweaking colors.

The simplest case is creating a uniform palette between two colors.
The method `Color.palette` does precisely that: interpolating a number of steps between two colors.
By default, this is done in `hls` space, which is better at interpolating the perceived level of brightness, but you can choose also `rgb` or `hsv` spaces if you're feeling adventurous.

Let's create a palette of ten colors between two well-known: sandy brown and steel blue:

```python title="color_spaces.py" hl_lines="3"
# ... (1)

colors = Color.palette(Colors.SandyBrown, Colors.SteelBlue, 10)

for i, color in enumerate(colors):
    sheet.select(".custom").children('div', nth=i+1).background(color).border(0.1, gray(0.4))

# ... (2)
```

1. Rest of the script hidden for simplicity.
2. Rest of the script hidden for simplicity.

Then we can apply these colors as usual to our markup, selecting the n-th child and applying the corresponding color:

```python title="color_spaces.py" hl_lines="5 6"
# ... (1)

colors = Color.palette(Colors.SandyBrown, Colors.SteelBlue, 10)

for i, color in enumerate(colors):
    sheet.select(".custom").children('div', nth=i+1).background(color).border(0.1, gray(0.4))

# ... (2)
```

## Becoming DRYer

As you have probably noticed, we haven't been very DRY so far. In fact, quite the opposite! We have writen what amounts to basically the same code three times for styling a full palette. Let's fix that now.

The simples solution is to write a method like the following:

```python
def palette(style: Style, colors:Sequence[Color]) -> Style:
    for i, color in enumerate(colors):
        style.children('div', nth=i+1).background(color).border(0.1, gray(0.4))

    return style
```

And this works, but it's a little ugly because it breaks our fluent API. Now we have to write something like:

```python
palette(sheet.select(...).<previous styles>).<posterior styles>
```

However, with a very small hack we can recover our fluent API. Just add `Style.palette = palette` to attach the function as a method to the `Style` class, and you can use it in chained calls just like a normal method!

With this little trick in place, let's refactor our three previous loops. This is what we end up with. Here we create the `palette` function:

```python title="color_spaces.py" hl_lines="3 4 5 7"
# ... (1)

def palette(style: Style, colors:Sequence[Color]) -> Style:
    for i, color in enumerate(colors):
        style.children('div', nth=i+1).background(color).border(0.1, gray(0.4))

Style.palette = palette

# Basic CSS colors
sheet.select(".basic").palette(Colors.basic_palette())

# All CSS colors by palette
for palette in Colors.palettes():
    sheet.select(f'.{palette}-colors').palette(Colors.palette(palette))

# Custom palette
sheet.select(".custom").palette(Color.palette(Colors.SandyBrown, Colors.SteelBlue, 10))

sheet.render("color-spaces.css")
```

1. Initial part of the script is hidden for simplicity.

And here we use it to create our palettes, replacing the unecessary repetition and inner loops:

```python title="color_spaces.py" hl_lines="10 13 14 17"
# ... (1)

def palette(style: Style, colors:Sequence[Color]) -> Style:
    for i, color in enumerate(colors):
        style.children('div', nth=i+1).background(color).border(0.1, gray(0.4))

Style.palette = palette

# Basic CSS colors
sheet.select(".basic").palette(Colors.basic_palette())

# All CSS colors by palette
for palette in Colors.palettes():
    sheet.select(f'.{palette}-colors').palette(Colors.palette(palette))

# Custom palette
sheet.select(".custom").palette(Color.palette(Colors.SandyBrown, Colors.SteelBlue, 10))

sheet.render("color-spaces.css")
```

1. Initial part of the script is hidden for simplicity.

??? warning "A word of caution"
    Beware, though, that even if we can use the previous trick to keep the fluent API, well, fluent, we still lost something. Specifically, we no longer have intellisense or completion after we call `.palette()`, basically because the type checker is, sadly, not smart enough to understand that after the call to `Style.palette = palette`, we now have a new method in the `Style` class.

    In the future we may have better type checkers capable of this sort of magic, but so far we're in tough luck. So, it is understandable if you prefer to keep things simple and use `palette` as a regular method, even if it breaks the aesthetics of the code, in favor of maintainability.
