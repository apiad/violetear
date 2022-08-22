# CSS transitions and animations

In this example we will build a simple vintage menu to showcase CSS transitions and animations. You can see the end result [here](animations.html). Try hovering over the menu items to see animations in action.

Let's begin by creating our simple markup:

```html title="animations.html"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Example: Animations: violetear</title>
    <link rel="stylesheet" href="animations.css">
</head>
<body>
    <div class="menu">
        <a class="menu-item" href="#">Home</a>
        <a class="menu-item" href="#">Products</a>
        <a class="menu-item" href="#">Pricing</a>
        <a class="menu-item" href="#">Documentation</a>
        <a class="menu-item" href="#">Contact</a>
    </div>
</body>
</html>
```

And style the menu with some fancy 90s Internet style (warning, this may hurt some designers' sensibilities).

```python title="animations.py"
from violetear import StyleSheet
from violetear.color import gray, red

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

# ...
```

## Basic transitions

With `violetear` it is very easy to configure a CSS transitions. Remember, `violetear` is just a thing layer on top of CSS, but because of its fluent design, Python code is often shorter (and closer) than the corresponding CSS code.

The most basic configuration for transition is using, you guessed it, the `transition()` method! Since we already selected and stored the `.menu-item` style in the `items` variable, we can reuse it to configure as many transitions as desired.

First, let's define the transition for `"background-color"` and at the same time configure the background color on hover:

```python title="animations.py" hl_lines="3"
# ...

items.transition("background-color").on("hover").background(gray(0.9))
items.transition("color", 300).on("hover").color(red(0.5))

# ...
```

The `transition` method receives property, duration, timing function, and delay, in that same order.
Sensible defaults are defined: "all" for transition property, `150ms` for duration, `linear` for timing function, and `0ms` for default delay.

Hence, we can apply a slower transition on the `"color"` property with a custom duration of `300ms`:

```python title="animations.py" hl_lines="4"
# ...

items.transition("background-color").on("hover").background(gray(0.9))
items.transition("color", 300).on("hover").color(red(0.5))

# ...
```

## Animating with CSS transforms

But if basic transitions are fun, then transforms are even better! With `violetear` it is easy to configure the CSS transform property using the [`Style.transform`](/violetear/api/violetear.style/#styletransform) method, which accepts parameters to define the translation, scale, and rotation separately.

However, for simplicity, we also have shorthand methods just for translating, scaling, and rotating.
Let's define a slightly more complex animation then, using all four transition sub-properties:

```python title="animations.py" hl_lines="7 8 9 10"
# ...

items.transition("background-color").on("hover").background(gray(0.9))
items.transition("color", 300).on("hover").color(red(0.5))

items.transition(
    property="transform",
    duration=150,
    timing="ease-in-out",
    delay=150,
).on("hover").scale(1.1).translate(y=5)
```

And we'll also configure a transformation on hover composed of a scaling and a translation:

```python title="animations.py" hl_lines="11"
# ...

items.transition("background-color").on("hover").background(gray(0.9))
items.transition("color", 300).on("hover").color(red(0.5))

items.transition(
    property="transform",
    duration=150,
    timing="ease-in-out",
    delay=150,
).on("hover").scale(1.1).translate(y=5)
```

"What's the fuss?", you might ask. Couldn't you just as easily defined the CSS rules individually with `Style.rule`? Well, yes, but if you look at the generated CSS you'll see something like this (look at the highlighted lines).

```css title="animations.css" hl_lines="10 11 12 13 19"
/* ... */

.menu-item {
    padding: 5px;
    border-width: 0.1rem;
    border-color: rgba(127,127,127,1.0);
    background-color: rgba(178,178,178,1.0);
    text-decoration: none;
    font-weight: 600;
    transition-property: background-color, color, transform;
    transition-duration: 150ms, 300ms, 150ms;
    transition-timing-function: linear, linear, ease-in-out;
    transition-delay: 0ms, 0ms, 150ms;
}

.menu-item:hover {
    background-color: rgba(229,229,229,1.0);
    color: rgba(255,0,0,1.0);
    transform: scaleX(1.1) scaleY(1.1) translateY(5px);
}

/* ... */
```

Both the `transition` and `transform` properties are somewhat especial in the sense that they can refer to an array of configurations. So, to write the previous code calling `rule()` explicitely, you would have needed to define all the properties, durations, timings, and delays together. Likewise with the transform scale, rotation and traslation.

Instead, when you call `transition` or `transform` to define individual states, `violetear` will keep track of the whole set of definitions and output the correct combined property values. It's a small piece of bookkeeping we do for you that is cumbersome to do on your own over and over.
