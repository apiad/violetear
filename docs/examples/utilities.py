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

from violetear.style import Style
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
    sheet.select(f".font-{weight}").font(weight=weight * 100)

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

# The simplest use case is defining a style where the variant names are the same
# as the attribute values.

# For example, here's how you define all font weight variants.

sheet.extend(
    UtilitySystem().define(
        clss="weight",  # :ref:clss:
        variants=["lighter", "normal", "bold", "bolder"],  # :ref:variants:
        rule=lambda style, variant: style.font(weight=variant),  # :ref:rule:
    )
)

# The `clss` argument gives a base name for the CSS class that will be created.
# In this case, we'll create classes called `weight-*`.

# :hl:clss:

# The `variants` argument generates the possible variant names.
# In this case we will have classes `weight-lighter`, ..., `weight-bolder`.

# :hl:variants:

# And the rule argument is a function that takes an empty style created
# for each specific variant and applies the necessary rules to configure it.
# In this case it will be called for times, each with an empty style selecting
# `.weight-lighter`, ..., `.weight-bolder` and the correspoding variant.

# :hl:rule:

# And this is the result:

# ```css linenums="990" title="utilites.css"
# ...
# :include:991:1005:utilities.css:
# ...
# ```

# A more advanced use case is when you pass an additional set of values to match the variants.
# In this case, the style for `.p-0` will match with value `0.0`, `.p-10` with value `4.0`,
# and correspondingly all in-between values.

sheet.extend(
    UtilitySystem().define(
        clss="p",
        variants=range(0, 11),
        values=Unit.scale(rem, 0, 4.0, 11),  # :hl:
        rule=lambda style, v: style.padding(v),
    )
)

# And here's how those rules look alike.

# ```css linenums="1006" title="utilites.css"
# ...
# :include:1007:1049:utilities.css:
# ...
# ```

# Of course, in the `rule` callable you can chain as many styling methods as you need.

sheet.extend(
    UtilitySystem().define(
        clss="shadow",
        variants=range(1, 6),
        rule=lambda style, v: style.color(Colors.Black).shadow(  # :hl:
            Colors.Black, x=v, y=v, blur=v, spread=v / 2  # :hl:
        ),  # :hl:
    )
)

# ```css linenums="1050" title="utilites.css"
# ...
# :include:1051:1072:utilities.css:
# ...
# ```

# If you pass a list of lists for variants, you'll get the cartesian product of all variants.
# Additionally, you can pass a `name` callable to define the name of the variant as well,
# and in this case you can forgo the `clss` parameter.

sheet.extend(
    UtilitySystem().define(
        variants=[Colors.basic_palette(), range(1, 10)],
        rule=lambda style, color, value: style.color(color.shade(value / 10)),
        name=lambda color, value: f"bg-{color.name.lower()}-{value*100}",
    )
)

# And just like that we created 16 * 9 background color utility classes.

# ```css linenums="1615" title="utilites.css"
# ...
# :include:1616:1629:utilities.css:
# ...
# ```

# Here's a more sophisticated example in which we want to create several
# subvariants, such as `pl-*` for `padding-left`, `pr-*`  for `padding-right`, etc.

sheet.extend(
    UtilitySystem().define(
        variants=[list("lrtb"), range(0, 11)],  # :ref:ex2_variants:
        values=[
            "left right top bottom".split(),
            Unit.scale(rem, 0.0, 4.0, 11),
        ],  # :ref:ex2_values:
        rule=lambda style, side, value: style.padding(
            **{side: value}
        ),  # :ref:ex2_rule:
        name=lambda side, value: f"p{side}-{value}",  # :ref:ex2_name:
    )
)

# Here's how that looks like when generated.

# ```css linenums="1694" title="utilites.css"
# ...
# :include:1695:1713:utilities.css:
# ...
# ```

# And here's how that works.
# Our variants will be the combinations of the characters `l`, `r`, `t` and `b`
# with the numbers from `1` to `10`.

# :hl:ex2_variants:

# The values will be correspondingly the combinations of `left`, `right`, `top` and `bottom` with
# the corresponding `rem` measure as computed using `Unit.scale`.

# :hl:ex2_values:

# Now, the magic happens in the `rule` callable, where we call `style.padding` but instead of
# explicitely passing an argument by name, we take advantage of Python's keyword operator `**`
# to call `padding` with the argument taken from `left`, `right`, etc., and the corresponding value.

# :hl:ex2_rule:

# Finally, since `p-l-3` is kind of a mouthful, we define a custom name function.
# Keep in mind that the `name` callable is called with the variants, not the values.

# :hl:ex2_name:

# And so you can see how easily we can create multiple variants of tiny rules.

# ??? warning "CSS files can get big quickly!"
#     You can easily see how quickly this approach leads to huge CSS files.
#     As convenient as it is to generate hundreds of tiny classes on-the-fly,
#     you will probably end up using less than 1% of those classes in any single file.
#
#     Fortunately, `violetear` has a few ways to render only the styles you use in a
#     a specific HTML file.
#     Read the [relevant section of the user guide](/violetear/guide/#minimizing-the-css-file) for more details.

if __name__ == "__main__":  # :skip:
    sheet.render("utilities.css")
