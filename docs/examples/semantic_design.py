# # Creating a semantic design system

# In this example we will create a simple semantic design system with
# classes for sizes (`sm`, `md`, ...) and roles (`primary`, `error`, ...).
# Using these clases we will style text and buttons.

# You can see the end result [here](./semantic-design.html),
# the corresponding CSS file [here](./semantic-design.css),
# and the Python script [here](./semantic_design.py).

from violetear import StyleSheet
from violetear.color import Colors
from violetear.units import Unit, rem

# As usual, we start with an empty stylesheet (except for normalization styles).

sheet = StyleSheet(normalize=True)  # :hl:
sheet.select("body").width(max=768).margin("auto")  # :ref:body_style:

# Then, we style our `body` with a proper size and margin to get some space.
# This has nothing to do with our design system, it's just to make the example page look better.

# :hl:body_style:

# ## Basic styles

# If you look at the HTML document, you'll notice we have some basic typography that we want
# to style with class `text`, as well as some buttons with class `btn`.

# ```html linenums="9" title="semantic-design.html"
# ...
# :include:10:19:semantic-design.html:
# ...
# ```

# ```html linenums="30"
# ...
# :include:31:36:semantic-design.html:
# ...
# ```


# We will begin by styling our `text` class with slightly lighter gray color.

base_text = sheet.select(".text").color(Colors.Black.lit(0.2))  # :hl:

base_btn = (
    sheet.select(".btn")
    .rule("cursor", "pointer")  # :ref:base_btn:
    .rounded()  # :ref:base_btn:
    .shadow(Colors.Black.transparent(0.2), x=2, y=2, blur=4)  # :ref:base_btn:
    .transition(duration=50)  # :ref:transition:
)

# And our `btn` class with a basic button-like style including a pointer cursor,
# rounded corners, and a light shadow.

# :hl:base_btn:

# With `transition` we also activate animated transitions with a very short
# duration (`50ms`). Check the [animations](../animations/) example for more details on this method.

# :hl:transition:

# ## Creating the size classes

# Semantic design systems often have classes like `sm`, `lg`, etc., that represent different sizes
# for the same type of element.
# In our system, we want to style things like `.text.sm` and `.btn.lg`, so we will define these size
# classes for both `.text` and `.btn`.

# First, we will create a scale of `rem` 5 values.

font_sizes = Unit.scale(rem, 0.8, 2.2, 5)

# Next, we will zip the class names with the corresponding sizes to create all size styles
# at once:

for cls, font in zip(["xs", "sm", "md", "lg", "xl"], font_sizes):  # :hl:
    text_size = sheet.select(f".text.{cls}").font(size=font)  # :ref:text_size:
    pd = font / 4  # :ref:button_size:
    btn_size = (
        sheet.select(f".btn.{cls}")
        .font(size=font)  # :ref:button_size:
        .padding(left=pd * 2, top=pd, bottom=pd, right=pd * 2)  # :ref:button_size:
    )

# For `.text` we just need to define the font size using the appropiate size.
# For example, selector `.text.xs` will have a font size of `0.8rem` and selector
# `.text.xl` will have a font size of `2.2rem`.

# :hl:text_size:

# For buttons, we will define a suitable padding value derived from the current size
# and set both the font size and the padding.

# :hl:button_size:

# ## Creating the color styles

# For color styles, we will define a custom palette of hand-picked colors.
# Some are darker, some are brighter.
# These will be the background colors of our semantic button classes.

colors = [
    Colors.White.lit(0.9),
    Colors.Blue.lit(0.3),
    Colors.Green.lit(0.3),
    Colors.Orange.lit(0.6),
    Colors.Red.lit(0.3),
    Colors.Cyan.lit(0.4),
]

# With these definitions we can create all our color styles in single loop.

for cls, color in zip("normal primary success warning error info".split(), colors):

    # First, the text style will simply define the color for each `.text.<cls>` selector.
    # For example, `.text.primary` will get a dark blue color.

    # Since some colors are darker and some are brighter, and for text we need
    # a consistent level of contrast, we will get the `0.2`-lightness version of
    # each color:

    text_style = sheet.select(f".text.{cls}").color(color.lit(0.2))

    # Now, for the buttons, we need to define the text color in a way that contrasts
    # with the background color. We use the `Color.lightness` property to select
    # between a darker and a lighter version of the background color.

    if color.lightness < 0.4:
        text_color = color.lit(0.9)
        accent_color = Colors.White
    else:
        text_color = color.lit(0.1)
        accent_color = Colors.Black

    # Now it's finally time to style the buttons.
    # We will need to style also the hover and active behaviours.

    # First, the raw button style, which simply assigns the corresponding
    # foreground and background colors to each semantic class.

    btn_style = sheet.select(f".btn.{cls}").background(color).color(text_color)  # :hl:
    hover = (
        btn_style.on("hover")
        .background(color.lighter(0.2))  # :ref:hover_style:
        .color(accent_color)  # :ref:hover_style:
    )
    active = (
        btn_style.on("active")
        .color(accent_color)  # :ref:active_style:
        .background(color.darker(0.1))  # :ref:active_style:
        .shadow(
            color.lit(0.2).transparent(0.2), x=0, y=0, blur=2, spread=1
        )  # :ref:active_style:
    )

    # The on-hover style will change to a slightly lighter version of the background color,
    # and choose either pure black or white for the foreground text color.
    # This will have the nice effect of lighting up or button a bit.

    # :hl:hover_style:

    # And finally, the active style will darken the background a bit, and move the shadow
    # so that it sits directly under the button, given the impression that it was indeed pressed:

    # :hl:active_style:

if __name__ == "__main__":  # :skip:
    sheet.render("semantic-design.css")
