# # Creating a library of utility classes

# Some design systems are based around utility classes, tiny styles that define one or a few rules
# for a single CSS concept.
# For example, classes like `text-xs`, `text-sm`, `text-lg`, etc., for different font sizes,
# or classes like `w-1`, `w-2`, etc., for different widths.

# In this example we will create a few of these utility classes to show you how you
# can leverage `violetear` to create hundreds of tiny CSS rules on the fly.
# We won't create utilities for everything, of course, because once you see the basic pattern,
# all that's left is doing the same over and over.

# Instead, we will focus on a few key patterns: font properties, geometry properties (padding, margin),
# and color palettes.

# As usual, we will create an empty stylesheet to begin.

from violetear.stylesheet import StyleSheet

sheet = StyleSheet(normalize=True)

# ## Defining text utilities

# For font sizes, we will create 5 different styles using `Unit.scale`.
# The classes will go from `text-xs` to `text-xl`.

from violetear.units import Unit, rem

sizes = Unit.scale(rem, 0.8, 3.0, 5)
labels = "xs sm md lg xl".split()

# Once we have all definitions in place, we can create all 5 classes with a single loop.

for size, label in zip(sizes, labels):
    sheet.select(f".text-{label}").font(size=size)

# Take a look at our [generated CSS](./utilities.css) and you'll see our newly created classes.

# ```css linenums="295" title="utilites.css"
# :include:295:313:utilities.css:
# ...
# ```

# Similary, we can define font weight style (`font-100`, ..., `font-900`) with a single loop:

for weight in range(1, 10):
    sheet.select(f".font-{weight}").font(weight=weight*100)

# And you can confirm that the 9 corresponding classes were created.

# ```css linenums="315" title="utilites.css"
# :include:315:350:utilities.css:
# ...
# ```

# ## Defining color classes

# Colors are even easier to create, since `violetear` already ships with lots
# of utilities for manipulating colors.

from violetear.color import Colors

# Let's start by creating the 9 variants of each of the basic colors.

for color in Colors.basic_palette():
    sheet.select(f".{color.name.lower()}").color(color)

    for i in range(1, 10):
        sheet.select(f".{color.name.lower()}-{i*100}").color(color.lit(i / 10))

# Again, check the CSS file and you'll lots and lots of color styles.

# ```css linenums="831" title="utilites.css"
# :include:831:869:utilities.css:
# ...
# ```

# ## Defining utility classes with presets

# Now that you get the basic idea, you can see how easy it is to build a full
# utility system.
# However, it is boring as hell to keep writing all those `for` loops zipping
# class names and values.
# For this reason, in `violetear.presets` you'll find a configurable `UtilitySystem`
# that helps you create these clases.

from violetear.presets import UtilitySystem

# The simplest use case is defining a rule where the variant names are the same
# as the attribute values.

# For example, here's how you define all `font-weight` variants.

sheet.extend(
    UtilitySystem().define(
        rule="font-weight",
        cls="weight",
        variants=["lighter", "normal", "bold", "bolder"],
    )
)

# And this is the result:

# ```css linenums="991" title="utilites.css"
# :include:991:1005:utilities.css:
# ...
# ```

# In a slightly more advanced use case you can pass an additional set of values to match the variants.

sheet.extend(
    UtilitySystem().define("padding", "p", range(0, 11), Unit.scale(rem, 0, 4.0, 11))
)

# And here's how those rules look alike.

# ```css linenums="991" title="utilites.css"
# :include:1007:1049:utilities.css:
# ...
# ```

# You can also pass a callable to create the variant values on-the-fly:

sheet.extend(
    UtilitySystem().define(
        "box-shadow", "shadow", range(1, 6), fn=lambda v: f"{v}px {v}px {v/2}rem gray"
    )
)

# ```css linenums="991" title="utilites.css"
# :include:1051:1069:utilities.css:
# ...
# ```

# If you pass a list of lists for variants, you'll get the cartesian product of all variants.
# Additionally, you can pass a `variant_name` callable to define the name of the variant as well.

sheet.extend(
    UtilitySystem().define(
        "background-color",
        "bg",
        [Colors.basic_palette(), range(1, 10)],
        fn=lambda color, value: color.shade(value / 10),
        variant_name=lambda color, value: f"{color.name.lower()}-{value*100}",
    )
)

# And just like that we created 16 * 9 background color utility classes.

# ```css linenums="1611" title="utilites.css"
# :include:1611:1629:utilities.css:
# ...
# ```

sheet.extend(
    UtilitySystem().define_many(
        rule="margin",
        subrules="left right top bottom".split(),
        clss="ml mr mt mb".split(),
        variants=range(0, 11),
        values=Unit.scale(rem, 0, 4.0, 11),
    )
)

# ```css linenums="1691" title="utilites.css"
# :include:1691:1713:utilities.css:
# ...
# ```

# ??? warning "CSS files can get big quickly!"
#     You can easily see how quickly this approach leads to huge CSS files.
#     As convenient as it is to generate hundreds of tiny classes on-the-fly,
#     you will probably end up using less than 1% of those classes in any single file.
#
#     Fortunately, `violetear` has a few ways to render only the styles you use in a
#     a specific HTML file.
#     Read the [relevant section of the user guide](/violetear/guide/#minimizing-the-css-file) for more details.

# And finally we render the CSS file.

if __name__ == "__main__":
    sheet.render("utilities.css")
