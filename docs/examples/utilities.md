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
from violetear.style import Style
from violetear.stylesheet import StyleSheet

sheet = StyleSheet(normalize=True)
```

## Defining text utilities

For font sizes, we will create 5 different styles using `Unit.scale`.
The classes will go from `text-xs` to `text-xl`.



```python linenums="20" title="utilities.py"
from violetear.units import Unit, rem

sizes = Unit.scale(rem, 0.8, 3.0, 5)
labels = "xs sm md lg xl".split()
```

Once we have all definitions in place, we can create all 5 classes with a single loop.



```python linenums="25" title="utilities.py"
for size, label in zip(sizes, labels):
    sheet.select(f".text-{label}").font(size=size)
```

Take a look at our [generated CSS](./utilities.css) and you'll see our newly created classes.

```css linenums="295" title="utilites.css"
.text-xs {
    font-size: 0.8rem;
}

.text-sm {
    font-size: 1.35rem;
}

.text-md {
    font-size: 1.9rem;
}

.text-lg {
    font-size: 2.45rem;
}

.text-xl {
    font-size: 3.0rem;
}
...
```

Similary, we can define font weight style (`font-100`, ..., `font-900`) with a single loop:



```python linenums="33" title="utilities.py"
for weight in range(1, 10):
    sheet.select(f".font-{weight}").font(weight=weight * 100)
```

And you can confirm that the 9 corresponding classes were created.

```css linenums="315" title="utilites.css"
.font-1 {
    font-weight: 100;
}

.font-2 {
    font-weight: 200;
}

.font-3 {
    font-weight: 300;
}

.font-4 {
    font-weight: 400;
}

.font-5 {
    font-weight: 500;
}

.font-6 {
    font-weight: 600;
}

.font-7 {
    font-weight: 700;
}

.font-8 {
    font-weight: 800;
}

.font-9 {
    font-weight: 900;
}

...
```

## Defining color classes

Colors are even easier to create, since `violetear` already ships with lots
of utilities for manipulating colors.



```python linenums="43" title="utilities.py"
from violetear.color import Colors
```

Let's start by creating the 9 variants of each of the basic colors.



```python linenums="45" title="utilities.py"
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
...
```

## Defining utility classes with presets

Now that you get the basic idea, you can see how easy it is to build a full
utility system.
However, it is boring as hell to keep writing all those `for` loops zipping
class names and values.
For this reason, in `violetear.presets` you'll find a configurable `UtilitySystem`
that helps you create these clases.



```python linenums="62" title="utilities.py"
from violetear.presets import UtilitySystem
```

The simplest use case is defining a style where the variant names are the same
as the attribute values.

For example, here's how you define all font weight variants.



```python linenums="66" title="utilities.py"
sheet.extend(
    UtilitySystem().define(
        clss="weight",  
        variants=["lighter", "normal", "bold", "bolder"],  
        rule=lambda style, variant: style.font(weight=variant),  
    )
)
```

The `clss` argument gives a base name for the CSS class that will be created.
In this case, we'll create classes called `weight-*`.



```python linenums="66" hl_lines="3" title="utilities.py"
sheet.extend(
    UtilitySystem().define(
        clss="weight",  
        variants=["lighter", "normal", "bold", "bolder"],  
        rule=lambda style, variant: style.font(weight=variant),  
    )
)
```


The `variants` argument generates the possible variant names.
In this case we will have classes `weight-lighter`, ..., `weight-bolder`.



```python linenums="66" hl_lines="4" title="utilities.py"
sheet.extend(
    UtilitySystem().define(
        clss="weight",  
        variants=["lighter", "normal", "bold", "bolder"],  
        rule=lambda style, variant: style.font(weight=variant),  
    )
)
```


And the rule argument is a function that takes an empty style created
for each specific variant and applies the necessary rules to configure it.
In this case it will be called for times, each with an empty style selecting
`.weight-lighter`, ..., `.weight-bolder` and the correspoding variant.



```python linenums="66" hl_lines="5" title="utilities.py"
sheet.extend(
    UtilitySystem().define(
        clss="weight",  
        variants=["lighter", "normal", "bold", "bolder"],  
        rule=lambda style, variant: style.font(weight=variant),  
    )
)
```


And this is the result:

```css linenums="990" title="utilites.css"
...
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
...
```

A more advanced use case is when you pass an additional set of values to match the variants.
In this case, the style for `.p-0` will match with value `0.0`, `.p-10` with value `4.0`,
and correspondingly all in-between values.



```python linenums="93" hl_lines="5" title="utilities.py"
sheet.extend(
    UtilitySystem().define(
        clss="p",
        variants=range(0, 11),
        values=Unit.scale(rem, 0, 4.0, 11),  
        rule=lambda style, v: style.padding(v),
    )
)
```

And here's how those rules look alike.

```css linenums="1006" title="utilites.css"
...
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
...
```

Of course, in the `rule` callable you can chain as many styling methods as you need.



```python linenums="108" hl_lines="5 6 7" title="utilities.py"
sheet.extend(
    UtilitySystem().define(
        clss="shadow",
        variants=range(1, 6),
        rule=lambda style, v: style.color(Colors.Black).shadow(  
            Colors.Black, x=v, y=v, blur=v, spread=v / 2  
        ),  
    )
)
```

```css linenums="1050" title="utilites.css"
...
.shadow-1 {
    color: rgba(0,0,0,1.0);
    box-shadow: 1px 1px 1px 0.5rem rgba(0,0,0,1.0);
}

.shadow-2 {
    color: rgba(0,0,0,1.0);
    box-shadow: 2px 2px 2px 1.0rem rgba(0,0,0,1.0);
}

.shadow-3 {
    color: rgba(0,0,0,1.0);
    box-shadow: 3px 3px 3px 1.5rem rgba(0,0,0,1.0);
}

.shadow-4 {
    color: rgba(0,0,0,1.0);
    box-shadow: 4px 4px 4px 2.0rem rgba(0,0,0,1.0);
}

.shadow-5 {
    color: rgba(0,0,0,1.0);
...
```

If you pass a list of lists for variants, you'll get the cartesian product of all variants.
Additionally, you can pass a `name` callable to define the name of the variant as well,
and in this case you can forgo the `clss` parameter.



```python linenums="125" title="utilities.py"
sheet.extend(
    UtilitySystem().define(
        variants=[Colors.basic_palette(), range(1, 10)],
        rule=lambda style, color, value: style.color(color.shade(value / 10)),
        name=lambda color, value: f"bg-{color.name.lower()}-{value*100}",
    )
)
```

And just like that we created 16 * 9 background color utility classes.

```css linenums="1615" title="utilites.css"
...
.bg-purple-100 {
    color: rgba(25,0,25,1.0);
}

.bg-purple-200 {
    color: rgba(51,0,51,1.0);
}

.bg-purple-300 {
    color: rgba(76,0,76,1.0);
}

.bg-purple-400 {
    color: rgba(102,0,102,1.0);
...
```

Here's a more sophisticated example in which we want to create several
subvariants, such as `pl-*` for `padding-left`, `pr-*`  for `padding-right`, etc.



```python linenums="140" title="utilities.py"
sheet.extend(
    UtilitySystem().define(
        variants=[list("lrtb"), range(0, 11)],  
        values=[
            "left right top bottom".split(),
            Unit.scale(rem, 0.0, 4.0, 11),
        ],  
        rule=lambda style, side, value: style.padding(
            **{side: value}
        ),  
        name=lambda side, value: f"p{side}-{value}",  
    )
)
```

Here's how that looks like when generated.

```css linenums="1694" title="utilites.css"
...

.pr-0 {
    padding-right: 0.0rem;
}

.pr-1 {
    padding-right: 0.4rem;
}

.pr-2 {
    padding-right: 0.8rem;
}

.pr-3 {
    padding-right: 1.2rem;
}

.pr-4 {
    padding-right: 1.6rem;
...
```

And here's how that works.
Our variants will be the combinations of the characters `l`, `r`, `t` and `b`
with the numbers from `1` to `10`.



```python linenums="140" hl_lines="3" title="utilities.py"
sheet.extend(
    UtilitySystem().define(
        variants=[list("lrtb"), range(0, 11)],  
        values=[
            "left right top bottom".split(),
            Unit.scale(rem, 0.0, 4.0, 11),
        ],  
        rule=lambda style, side, value: style.padding(
            **{side: value}
        ),  
        name=lambda side, value: f"p{side}-{value}",  
    )
)
```


The values will be correspondingly the combinations of `left`, `right`, `top` and `bottom` with
the corresponding `rem` measure as computed using `Unit.scale`.



```python linenums="140" hl_lines="7" title="utilities.py"
sheet.extend(
    UtilitySystem().define(
        variants=[list("lrtb"), range(0, 11)],  
        values=[
            "left right top bottom".split(),
            Unit.scale(rem, 0.0, 4.0, 11),
        ],  
        rule=lambda style, side, value: style.padding(
            **{side: value}
        ),  
        name=lambda side, value: f"p{side}-{value}",  
    )
)
```


Now, the magic happens in the `rule` callable, where we call `style.padding` but instead of
explicitely passing an argument by name, we take advantage of Python's keyword operator `**`
to call `padding` with the argument taken from `left`, `right`, etc., and the corresponding value.



```python linenums="140" hl_lines="10" title="utilities.py"
sheet.extend(
    UtilitySystem().define(
        variants=[list("lrtb"), range(0, 11)],  
        values=[
            "left right top bottom".split(),
            Unit.scale(rem, 0.0, 4.0, 11),
        ],  
        rule=lambda style, side, value: style.padding(
            **{side: value}
        ),  
        name=lambda side, value: f"p{side}-{value}",  
    )
)
```


Finally, since `p-l-3` is kind of a mouthful, we define a custom name function.
Keep in mind that the `name` callable is called with the variants, not the values.



```python linenums="140" hl_lines="11" title="utilities.py"
sheet.extend(
    UtilitySystem().define(
        variants=[list("lrtb"), range(0, 11)],  
        values=[
            "left right top bottom".split(),
            Unit.scale(rem, 0.0, 4.0, 11),
        ],  
        rule=lambda style, side, value: style.padding(
            **{side: value}
        ),  
        name=lambda side, value: f"p{side}-{value}",  
    )
)
```


And so you can see how easily we can create multiple variants of tiny rules.

??? warning "CSS files can get big quickly!"
    You can easily see how quickly this approach leads to huge CSS files.
    As convenient as it is to generate hundreds of tiny classes on-the-fly,
    you will probably end up using less than 1% of those classes in any single file.

    Fortunately, `violetear` has a few ways to render only the styles you use in a
    a specific HTML file.
    Read the [relevant section of the user guide](/violetear/guide/#minimizing-the-css-file) for more details.

