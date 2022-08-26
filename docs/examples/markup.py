# # Generating markup

# This example will show you how to generate HTML markup completely on-the-fly from
# Python code, using the classes from `violetear.markup`.
# You can use this functionality to quickly create prototype markup to visualize or debug
# your styles.

# !!! note
#     Even though `violetear` can render arbitrary HTML, this functionality is **not** intended
#     to replace a proper template engine like Jinja.
#
#     The functionality in `violetear.markup` is only intended to be used for prototyping and
#     testing. `violetear` will never aim to become a production-ready HTML rendering engine.
#     That being said, it is pretty cool!

# ## Basic setup

# Everything starts from the `Page` class.
# At this point you can define a title.

from violetear.color import Colors
from violetear.markup import Element, Page
from violetear.style import Style
from violetear.stylesheet import StyleSheet

page = Page(title="Example: Markup - violetear")

# We can also add stylesheets to our page that will be rendered either inline or as separate files.

sheet = StyleSheet(normalize=True)

page.style(sheet, inline=False, name="markup.css")

if __name__ == "__main__":  # :skip:
    page.render("markup.html")

# Just with this let's take a look at the resulting HTML file.

# ```html title="markup.html" linenums="1"
# :include:1:9:markup.html:
# ...
# ```

# ## Adding elements to the body

# There are a couple ways to add elements to a page.
# Let's start with the most basic ones.

# You can manually create `Element` instances and add them to the body.

page.body.add(Element("h1", classes=["title"], text="This is a header"))

# Elements can have child elements.

page.body.add(
    Element(
        "ul",
        Element("li", text="First item"),
        Element("li", text="Second item"),
        Element("li", text="Third item"),
    )
)

# And you can add inline styles using the `Style` class, in all its fluent glory!

page.body.add(
    Element(
        "span",
        text="A styled text!",
        style=Style().font(14).color(Colors.Red),
    )
)

if __name__ == "__main__":  # :skip:
    page.render("markup.html")

# As you might expect, this is the HTML file you get.

# ```html title="markup.html" linenums="1"
# :include:1:27:markup.html:
# ...
# ```

# ## Using the fluent API to add elements

# And while this works, it is rather cumbersome. For this reason,
# the `Element` class gives you a fluent interface with the `Element.create` method
# which creates and adds a new child element, and returns it so you can chain additional
# method calls such as styling options.

# A common pattern is to chain `Style` method calls.

page.body.create("div", "container", id="main").style.margin("auto").width(max=768)

# However, this pattern breaks the fluent API because it returns the `Style` instance.
# To stay in flow, we can use the `styled` method that receives a callable to be applied
# to the internal style, but returns the current element, so you can obtain a reference to
# last element created for further method calls.

# For example, we can create a div and style it.

ul = (
    page.body.create("div", "container fluid")  # :hl:
    .styled(lambda s: s.margin("auto").width(max=768))  # :hl:
    .create("ul")  # :ref:ul:
    .styled(lambda s: s.padding(5, bottom=10))  # :ref:ul:
)

for i in range(5):  # :ref:li:
    ul.create("li", text=f"The {i+1}th element!")  # :ref:li:

# Then chain another call to create a `ul` and style it:

# :hl:ul:

# And then we can just keep building from the `ul` element.

# :hl:li:

if __name__ == "__main__":  # :skip:
    page.render("markup.html")

# Take a look to the newly created tags.

# ```html title="markup.html" linenums="29"
# ...
# :include:30:48:markup.html:
# ...
# ```

# But it gets better, we can achieve the same result as before without having
# to break the flow, by using `spawn` to create multiple children.

div = (
    page.body.create("div", "container")
    .styled(lambda s: s.margin("auto").width(max=768))
    .create("ul")
    .styled(lambda s: s.padding(5, bottom=10))
    .spawn(  # :hl:
        5,  # :ref:spawn1:
        "li",  # :ref:spawn1:
        classes="item", # :ref:spawn2:
        text=lambda i: f"The {i+1}th element", # :ref:spawn2:
        style=lambda i: Style().color(Colors.Blue.shade(i / 5)), # :ref:spawn2:
    )
    .parent() # :ref:parent:
)

# The syntax is very similar to `create` except that it receives a number of items to create
# along with the tag.

# :hl:spawn1:

# And you can pass either direct values or callables to compute the values for the children attributes.

# :hl:spawn2:

# Finally, contrary to the `create` method which returns the newly created element,
# the `spawn` method returns the same element on which you call it, in this case, the `ul`.
# We can then use `parent` to navigate up and continue chaining method calls.

# :hl:parent:

# So here's the result.

# ```html title="markup.html" linenums="48"
# ...
# :include:49:67:markup.html:
# ...
# ```

if __name__ == "__main__":  # :skip:
    page.render("markup.html")
