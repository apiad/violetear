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

# Everything starts from the `Document` class.
# At this point you can define a title.

from violetear.markup import Element, Document
from violetear.stylesheet import StyleSheet

doc = Document(title="Example: Markup - violetear")

# We can also add stylesheets to our page that will be rendered either inline or as separate files.

sheet = StyleSheet(normalize=True)

doc.style(sheet, inline=False, name="markup.css")

# Just with this let's take a look at the resulting HTML file.

# ```html title="markup.html" linenums="1"
# :include:1:9:markup.html:
# ...
# ```

# ## Adding elements to the body

# There are a couple ways to add elements to a page.
# Let's start with the most basic ones.

# You can manually create `Element` instances and add them to the body.

doc.body.add(Element("h1", classes=["title"], text="This is a header"))

# Elements can have child elements.

doc.body.add(
    Element(
        "ul",
        Element("li", text="First item"),
        Element("li", text="Second item"),
        Element("li", text="Third item"),
    )
)

# And you can add inline styles using the `Style` class, in all its fluent glory!

from violetear.style import Style
from violetear.color import Colors


doc.body.add(
    Element(
        "span",
        text="A styled text!",
        style=Style().font(14).color(Colors.Red),
    )
)

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

doc.body.create("div", "container", id="main").style.margin("auto").width(max=768)

# However, this pattern breaks the fluent API because it returns the `Style` instance.
# To stay in flow, we can use the `styled` method that receives a callable to be applied
# to the internal style, but returns the current element, so you can obtain a reference to
# last element created for further method calls.

# For example, we can create a div and style it.

ul = (
    doc.body.create("div", "container fluid")  # :hl:
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

# Take a look to the newly created tags.

# ```html title="markup.html" linenums="29"
# ...
# :include:30:48:markup.html:
# ...
# ```

# But it gets better, we can achieve the same result as before without having
# to break the flow, by using `spawn` to create multiple children.

div = (
    doc.body.create("div", "container")
    .create("ul")
    .spawn(  # :hl:
        5,  # :ref:spawn1:
        "li",  # :ref:spawn1:
        classes="item",  # :ref:spawn2:
        text=lambda i: f"The {i+1}th element",  # :ref:spawn2:
        style=lambda i: Style().color(Colors.Blue.shade(i / 5)),  # :ref:spawn2:
    )
    .styled(lambda s: s.padding(5, bottom=10))  # :ref:ul_style:
    .parent()  # :ref:parent:
    .styled(lambda s: s.margin("auto").width(max=768))  # :ref:parent:
)

# The syntax is very similar to `create` except that it receives a number of items to create
# along with the tag.

# :hl:spawn1:

# And you can pass either direct values or callables to compute the values for the children attributes.

# :hl:spawn2:

# Finally, contrary to the `create` method which returns the newly created element,
# the `spawn` method returns the same element on which you call it, in this case, the `ul`,
# which we then proceed to style.

# :hl:ul_style:

# We can then use `parent` to navigate up and continue chaining method calls,
# for example, to style the first `div` element we created.

# :hl:parent:

# Notice how we went down the tree creating and then up the tree styling.
# In the same way, we could have called `style` just after each `create`.

# Here's the result.

# ```html title="markup.html" linenums="48"
# ...
# :include:49:67:markup.html:
# ...
# ```

# ## Defining and using components

# So far we've been using the basic API which lets you create any type of HTML element.
# However, this API can quickly become repetitive as you add similar markup for similar concepts.
# If you want to create custom abstractions, like a menu, which may consitst of several
# markup elements (a <div> with a <ul> inside, several `span`s, etc.,),
# things can easily become convoluted.

# One simple solution is to encapsulate your custom markup logic in a function, something like:

# ```python
# def menu(*items):
#     return (
#         Element("div")
#         .create("ul")
#         .spawn(len(items), "li", text=lambda i: items[i])
#         .parent()
#     )
# ```

# And then use it like:

# ```python
# doc.body.add(menu("Home", "Products", "Pricing", "Abouts"))
# ```

# And while this works, it is a bit ugly for a couple of reasons.
# First, you need to remember to add that `parent()` at the end to make sure to return
# the `div` and not the `ul`, and as soon as you start complicating your markup logic a bit
# it is highly likely that you will return the wrong element a few items.

# But the main reason is that even though we encapsulated the concept of a menu,
# we didn't *abstracted* it.
# The minute we invoke the encapsulated functionality we lost the menu abstraction and
# we are left with a regular `div` with an `ul` and a bunch of `li`s inside.

# For example, if you want to add a new item to your menu after created, what can you do?
# There is no real abstraction of a menu that you can reference and modify.
# What you want, of course, is a `Menu` class that you can instantiate and add
# to a `Document`, manipulate at your will, and only on render time
# expand it into the actual markup elements.

# We can achieve that by inheriting from the `Component` class.

from violetear.markup import Component  # :hl:


class Menu(Component):  # :hl:
    def __init__(self, **entries: str) -> None:
        super().__init__()
        self.entries = dict(**entries)  # :ref:menu_constructor:

    def compose(self) -> Element:  # :ref:menu_compose:
        return Element(
            "div",
            Element(
                "ul",
                *[
                    Element("li", classes="menu-item").add(
                        Element("a", text=key, href=value)
                    )
                    for key, value in self.entries.items()
                ],
            ),
            classes="menu",
        )


# Which we can instantiate as usual and add to our document:

menu = Menu(
    Home="/",
    Products="/products",
    Pricing="/pricing",
    About="/about-us",
)

doc.body.add(menu)

# But if we modify the menu before rendering, it will work.
# We can manipulate the abstraction directly, not the underlying HTML markup that
# only will exist at render time.

menu.entries["Services"] = "/services"

# Here's the end result:

# ```html title="markup.py" linenums="67"
# ...
# :include:68:96:markup.html:
# ...
# ```

# The magic happens in two places. First, when we create the `Menu` instance,
# we pass the items as a mapping and store it in the instance.

# :hl:menu_constructor:

# And then in the `compose` method we simply build our markup as desired using
# the fluent API, the regular `add` method, the constructor syntax, etc.

# :hl:menu_compose:

# Now, if this still looks a bit ugly to you, we can make it even better.
# Part of the problem is that the menu items are themselves another abstraction
# that we are using implicitly. Let's make it explicit.


class MenuItem(Component):
    def __init__(self, name, href) -> None:
        super().__init__()
        self.name = name
        self.href = href

    def compose(self) -> Element:
        return Element(
            "li", Element("a", text=self.name, href=self.href), classes="menu-item"
        )


# And then we can redefine our `Menu` class to make explicit use of these items:


class Menu(Component):
    def __init__(self, **entries) -> None:
        super().__init__()
        self.content.extend(
            MenuItem(name=key, href=value)  # :ref:menu_item:
            for key, value in entries.items()  # :ref:menu_item:
        )

    def compose(self) -> Element:
        return Element(
            "div", Element("ul", *self.content), classes="menu"  # :ref:menu_item:
        )


# On render time, `compose` will be called recursively on all children `Components`,
# so can safely mix `Component`s and regular `Element`s and everything will work out just fine.

# Thus, now we can on the constructor create child elements of type `MenuItem`,
# and make sure to inject them at the right location in the markup we build at `compose`.

# :hl:menu_item:

# It doesn't seem like we've gained much with this pattern but now we have made our `Menu`
# abstraction fully compatible with the `Element` API, so we can do things like freely
# mixing `Menu` and `MenuItem` with regular `Element`s  for ultimate flexibility
# plus maximum expresivity.

doc.body.add(
    Menu().extend(
        MenuItem("Home", "/"),
        MenuItem("Pricing", "/pricing"),
        MenuItem("Products", "/products"),
        Element("div", classes="divider"),  # :hl:
        MenuItem("About", "/about-us"),
    )
)

# > The `extend` method just calls `add` for each item.

# And the generated HTML blends perfectly the markup generated from the `compose` methods
# with the explicit markup.

# ```html title="markup.html" linenums="96" hl_lines="19 20"
# ...
# :include:97:122:markup.html:
# ...
# ```

# ??? note "Unopinionated to its core"
#     Remember that `violetear` is totally unopinionated.
#     We will never dictate how you have to structure your HTML or CSS.
#     We simply give you the tools to build whatever abstraction you prefer.
#
#     If you want to hack a simple HTML over a weekend you can use the fluent API
#     and get away with it.
#     If you're building something durable enough to deserve a complete design
#     system with custom components, `violetear` can help you there as well.


if __name__ == "__main__":  # :skip:
    doc.render("markup.html")
