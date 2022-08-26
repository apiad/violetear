# Creating a library of utility classes

Some design systems are based around utility classes, tiny styles that define one or a few rules
for a single CSS concept.
For example, classes like `text-xs`, `text-sm`, `text-lg`, etc., for different font sizes,
or classes like `w-1`, `w-2`, etc., for different widths.

In this example we will create a few of these utility classes to show you how you
can leverage `violetear` to create hundreds of tiny CSS rules on the fly.
We won't create utilities for everything, of course, because once you see the basic pattern,
all that's left is doing the same over and over.

Instead, we will focus on a few key patterns: font properties, geometry properties (padding, margin),
and color palettes.

As usual, we will create an empty stylesheet to begin.



```python linenums="13" title="utilities.py"
from violetear.stylesheet import StyleSheet

sheet = StyleSheet(normalize=True)
```

## Defining text utilities

For font sizes, we will create 5 different styles using `Unit.scale`.
The classes will go from `text-xs` to `text-xl`.



```python linenums="19" title="utilities.py"
from violetear.units import Unit, rem

sizes = Unit.scale(rem, 0.8, 3.0, 5)
labels = "xs sm md lg xl".split()
```

Once we have all definitions in place, we can create all 5 classes with a single loop.



```python linenums="24" title="utilities.py"
for size, label in zip(sizes, labels):
    sheet.select(f".text.{label}").font(size=size)
```

Take a look at our [generated CSS](./utilities.css) and you'll see our newly created classes.

```css linenums="295" title="utilites.css"
.text.xs {
    font-size: 0.8rem;
}

.text.sm {
    font-size: 1.35rem;
}

.text.md {
    font-size: 1.9rem;
}

.text.lg {
    font-size: 2.45rem;
}

.text.xl {
    font-size: 3.0rem;
}
```

Similary, we can define font weight style (`font-100`, ..., `font-900`) with a single loop:



```python linenums="31" title="utilities.py"
for weight in range(100, 1000, 100):
    sheet.select(f".font-{weight}").font(weight=weight)
```

And you can confirm that the 9 corresponding classes were created.

```css linenums="315" title="utilites.css"
.font-100 {
    font-weight: 100;
}

.font-200 {
    font-weight: 200;
}

.font-300 {
    font-weight: 300;
}

.font-400 {
    font-weight: 400;
}

.font-500 {
    font-weight: 500;
}

.font-600 {
    font-weight: 600;
}

.font-700 {
    font-weight: 700;
}

.font-800 {
    font-weight: 800;
}

.font-900 {
    font-weight: 900;
}

```

## Defining color classes

Colors are even easier to create, since `violetear` already ships with lots
of utilities for manipulating colors.



```python linenums="40" title="utilities.py"
from violetear.color import Colors
```

Let's start by creating the 9 variants of each of the basic colors.



```python linenums="42" title="utilities.py"
for color in Colors.basic_palette():
    sheet.select(f".{color.name.lower()}").color(color)

    for i in range(1, 10):
        sheet.select(f".{color.name.lower()}-{i*100}").color(color.lit(i / 10))
```

Again, check the CSS file and you'll lots and lots of color styles.

```css linenums="831" title="utilites.css"
.blue {
    color: rgba(0,0,255,1.0);
}

.blue-100 {
    color: rgba(0,0,51,1.0);
}

.blue-200 {
    color: rgba(0,0,102,1.0);
}

.blue-300 {
    color: rgba(0,0,153,1.0);
}

.blue-400 {
    color: rgba(0,0,204,1.0);
}

.blue-500 {
    color: rgba(0,0,255,1.0);
}

.blue-600 {
    color: rgba(50,50,255,1.0);
}

.blue-700 {
    color: rgba(101,101,255,1.0);
}

.blue-800 {
    color: rgba(153,153,255,1.0);
}

.blue-900 {
    color: rgba(204,204,254,1.0);
}
```

## Defining utility classes with presets

Now that you get the basic idea, you can see how easy it is to build a full
utility system.
However, it is boring as hell to keep writing all those `for` loops zipping
class names and values.
For this reason, in `violetear.presets` you'll find a configurable `UtilitySystem`
that helps you create these clases.



```python linenums="58" title="utilities.py"
from violetear.presets import UtilitySystem
```

The simplest use case is defining a rule where the variant names are the same
as the attribute values.

For example, here's how you define all `font-weight` variants.



```python linenums="62" title="utilities.py"
sheet.extend(
    UtilitySystem().define(
        rule="font-weight",
        cls="weight",
        variants=["lighter", "normal", "bold", "bolder"],
    )
)
```

And this is the result:

```css linenums="991" title="utilites.css"
.weight-lighter {
    font-weight: lighter;
}

.weight-normal {
    font-weight: normal;
}

.weight-bold {
    font-weight: bold;
}

.weight-bolder {
    font-weight: bolder;
}
```

In a slightly more advanced use case you can pass an additional set of values to match the variants.



```python linenums="74" title="utilities.py"
sheet.extend(
    UtilitySystem().define("padding", "p", range(0, 11), Unit.scale(rem, 0, 4.0, 11))
)
```

And here's how those rules look alike.

```css linenums="991" title="utilites.css"
.p-0 {
    padding: 0rem;
}

.p-1 {
    padding: 0.4rem;
}

.p-2 {
    padding: 0.8rem;
}

.p-3 {
    padding: 1.2rem;
}

.p-4 {
    padding: 1.6rem;
}

.p-5 {
    padding: 2.0rem;
}

.p-6 {
    padding: 2.4rem;
}

.p-7 {
    padding: 2.8rem;
}

.p-8 {
    padding: 3.2rem;
}

.p-9 {
    padding: 3.6rem;
}

.p-10 {
    padding: 4.0rem;
}
```

You can also pass a callable to create the variant values on-the-fly:



```python linenums="82" title="utilities.py"
sheet.extend(
    UtilitySystem().define(
        "box-shadow", "shadow", range(1, 6), fn=lambda v: f"{v}px {v}px {v/2}rem gray"
    )
)
```

```css linenums="991" title="utilites.css"
.shadow-1 {
    box-shadow: 1px 1px 0.5rem gray;
}

.shadow-2 {
    box-shadow: 2px 2px 1.0rem gray;
}

.shadow-3 {
    box-shadow: 3px 3px 1.5rem gray;
}

.shadow-4 {
    box-shadow: 4px 4px 2.0rem gray;
}

.shadow-5 {
    box-shadow: 5px 5px 2.5rem gray;
}
```

If you pass a list of lists for variants, you'll get the cartesian product of all variants.
Additionally, you can pass a `variant_name` callable to define the name of the variant as well.



```python linenums="92" title="utilities.py"
sheet.extend(
    UtilitySystem().define(
        "background-color",
        "bg",
        [Colors.basic_palette(), range(1, 11)],
        fn=lambda color, value: color.shade(value / 10),
        variant_name=lambda color, value: f"{color.name.lower()}-{value*100}",
    )
)
```

And just like that we created 16 * 9 background color utility classes.

```css linenums="991" title="utilites.css"
.bg-purple-100 {
    background-color: rgba(25,0,25,1.0);
}

.bg-purple-200 {
    background-color: rgba(51,0,51,1.0);
}

.bg-purple-300 {
    background-color: rgba(76,0,76,1.0);
}

.bg-purple-400 {
    background-color: rgba(102,0,102,1.0);
}

.bg-purple-500 {
    background-color: rgba(128,0,128,1.0);
}
```



```python linenums="105" title="utilities.py"
sheet.extend(
    UtilitySystem().define_many(
        "margin",
        "left right top bottom".split(),
        "ml mr mt mb".split(),
        range(0, 11),
        Unit.scale(rem, 0, 4.0, 11),
    )
)
```

And finally we render the CSS file.



```python linenums="115" title="utilities.py"
if __name__ == "__main__":
    sheet.render("utilities.css")
```

