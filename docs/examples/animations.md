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

## Using custom animations

And finally, just because we're into this vintage frenzy, let's add a good old scrolling text with animating color change.

First, let's add some seemingly profound text.

```html title="animations.html"
<!-- ... -->
<body>
    <!-- ... -->
    <div class="marquee">
        <p>
            Sint nesciunt architecto ipsam quia. <br>
            Deleniti explicabo fuga velit. <br>
            Iste occaecati sunt veniam veniam quas ratione nihil. <br>
            Velit nam eum in a nam ratione. <br> <br>
            Aut quo culpa alias voluptates voluptatem debitis et aperiam. <br>
            Et illo qui quae. <br>
            Alias aut repellat quidem et cum aut. <br>
            Repudiandae doloribus vero quibusdam veniam nam in. <br> <br>
            Voluptas ut rerum aut harum libero. <br>
            Qui sint et sapiente non fugiat soluta commodi. <br>
            Deserunt ipsum quo autem. <br>
            Inventore in et dolorem. <br>
            Enim nobis in quia quisquam dolorem similique eos. <br>
            Repellat eum consequatur sunt velit eum earum hic tenetur. <br>
        </p>
    </div>
</body>
```

Next, we'll style the container div with hidden overflow to avoid changing the viewport size when the text scrolls. We'll also style the text with some basic rules, including relative positioning so that it flows freely within its container.

```python title="annotations.py"
# ...

sheet.select(".marquee").height(500).rules(overflow="hidden").padding(20)
text = sheet.select("p").font(size=22, weight=100).relative()

# ...
```

??? note "Adding custom rules"

    You should have notice the use of `.rules(overflow="hidden")`. In general, when
    there's no shorthand method in the `Style` class, you can always use either
    `Style.rule` to define a single CSS rule, or `Style.rules` which takes keyword arguments
    as attribute names, so you can define several rules at a time.

    This method also automatically converts `_` to `-` in attribute names so you can use it like:

    ```python
    sheet.select(...).rules(text_decoration_color=red(0.8))
    ```

    Which is equivalent to:

    ```python
    sheet.select(...).rule('text-decoration-color', red(0.8))
    ```

    Feel free to choose the method that is more convenient for yourself. In the meantime, as `violetear` grows, we will keep adding shorthand methods for the most common CSS attributes, but we will probably never achieve 100% coverage, nor we aim to, so these methods will remain an alternative for setting very niche attributes.

Now it's time to let our imagination fly and add some animations! In `violetear` you can use the `Animation` class to quickly create complex animations. Let's start with the simplest case, creating an animation that moves the text upwards:

```python title="animations.py" hl_lines="6 7 8 9 10"
# ...

sheet.select(".marquee").height(500).rules(overflow="hidden").padding(20)
text = sheet.select("p").font(size=22, weight=100).relative()

animation = (
    Animation("text-up")
    .start(top=px(500))
    .end(top=px(-500))
)

text.animation(animation, duration=sec(10), iterations='infinite')
```

The methods `start` and `end` define the initial and final keyframes. They are equivalent to calling [`Animation.at`](/violetear/api/violetear.animation#Animation.at) with `0`  and `1` respectively. Like `Style.rules`, these methods can receive keyword-based attributes in the case where you just need to animate a few simple attributes.

However, when you want to create a somewhat complex animation, it is convenient to use the `Style` fluent API. In this case, the `at`, `start` and `end` methods also accept a `Style` instance. Let's add a couple more keyframes to illustrate this:


```python title="animations.py" hl_lines="9 10 11"
# ...

sheet.select(".marquee").height(500).rules(overflow="hidden").padding(20)
text = sheet.select("p").font(size=22, weight=100).relative()

animation = (
    Animation("text-up")
    .start(top=px(500))
    .at(0.25, Style().color(green(0.3)))
    .at(0.50, Style().color(blue(0.3)).font(weight=900))
    .at(0.75, Style().color(red(0.3)))
    .end(top=px(-500))
)

text.animation(animation, duration=sec(10), iterations='infinite')
```

Finally, we configure the animation using the `Style.animation` method, which references an existing animation, and sets the duration, number of iterations, and other parameters.

```python title="animations.py" hl_lines="15"
# ...

sheet.select(".marquee").height(500).rules(overflow="hidden").padding(20)
text = sheet.select("p").font(size=22, weight=100).relative()

animation = (
    Animation("text-up")
    .start(top=px(500))
    .at(0.25, Style().color(green(0.3)))
    .at(0.50, Style().color(blue(0.3)).font(weight=900))
    .at(0.75, Style().color(red(0.3)))
    .end(top=px(-500))
)

text.animation(animation, duration=sec(10), iterations='infinite')
```

Looking at the generated CSS, you'll notice the `@keyframes` declaration that corresponds to our animation:

```css title="animations.css"
/* ... */

p {
    font-size: 22px;
    font-weight: 100;
    position: relative;
    animation-name: text-up;
    animation-duration: 10s;
    animation-timing-function: linear;
    animation-iteration-count: infinite;
}

@keyframes text-up {
    0.0%  {
        top: 500px;
    }

    25.0%  {
        color: rgba(0,153,0,1.0);
    }

    50.0%  {
        color: rgba(0,0,153,1.0);
        font-weight: 900;
    }

    75.0%  {
        color: rgba(153,0,0,1.0);
    }

    100.0%  {
        top: -500px;
    }

}
```