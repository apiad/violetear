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

doc.style(sheet, inline=False, href="markup.css")

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

# To stay in flow, we can use the `style` method that receives a callable to be applied
# to the internal style, but returns the current element, so you can obtain a reference to
# last element created for further method calls.

# For example, we can create a div and style it.

ul = (
    doc.body.create("div")  # :hl:
    .style(Style().margin("auto").width(max=768))  # :hl:
    .create("ul")  # :ref:ul:
    .style(Style().padding(5, bottom=10))  # :ref:ul:
)

for i in range(5):  # :ref:li:
    ul.create("li").text(f"The {i+1}th element!")  # :ref:li:

# Then chain another call to create a `ul` and style it:

# :hl:ul:

# And then we can just keep building from the `ul` element.

# :hl:li:

# Take a look to the newly created tags.

# ```html title="markup.html" linenums="27"
# ...
# :include:28:46:markup.html:
# ...
# ```

# But it gets better, we can achieve the same result as before without having
# to break the flow, by using `spawn` to create multiple children.

div = (
    doc.body.create("div")
    .classes("container")
    .create("ul")
    .spawn(5, "li")  # :hl:
    .each(
        lambda i, item: item.text(f"The {i+1}th element").style(  # :ref:spawn2:
            Style().color(Colors.Blue.shade(i / 5))  # :ref:spawn2:
        )  # :ref:spawn2:
    )
    .parent()  # :ref:ul_style:
    .style(Style().padding(5, bottom=10))  # :ref:ul_style:
    .parent()  # :ref:parent:
    .style(Style().margin("auto").width(max=768))  # :ref:parent:
)

# The syntax is very similar to `create` except that it receives a number of items to create
# along with the tag.

# This method returns an `ElementSet` with all the created items.
# The `each` method can be used to configure each individual item, receiving both
# the item and its index.

# :hl:spawn2:

# After finishing styling the children, we need to call `parent` to jump back to the `ul`,
# which we then proceed to style.

# :hl:ul_style:

# We can then use `parent` again to navigate up and continue chaining method calls,
# for example, to style the first `div` element we created.

# :hl:parent:

# Notice how we went down the tree creating and then up the tree styling.
# In the same way, we could have called `style` just after each `create`.

# Here's the result.

# ```html title="markup.html" linenums="46"
# ...
# :include:47:65:markup.html:
# ...
# ```

# ## Defining and using components

# So far we've been using the basic API which lets you create any type of HTML element.
# However, this API can quickly become repetitive as you add similar markup for similar concepts.
# If you want to create custom abstractions, like a menu, which may consitst of several
# markup elements (a `div` with a `ul` inside, several `span`s, etc.,),
# things can easily become convoluted.

# One simple solution is to encapsulate your custom markup logic in a function, something like:

# ```python
# def menu(*items):
#     return (
#         Element("div")
#         .create("ul")
#         .spawn(len(items), "li")
#         .each(lambda i, item: item.text(items[i]))
#         .root()
#     )
# ```

# > :information_source: The `root` method returns the top-most element in a hierarchy, i.e., the `div` in this case.

# And then use it like:

# ```python
# doc.body.add(menu("Home", "Products", "Pricing", "Abouts"))
# ```

# And while this works, it is unsatisfying because even though we encapsulated the concept of a menu,
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

    def compose(self, content) -> Element:
        return (
            Element("div")  # :ref:menu_compose:
            .classes("menu")  # :ref:menu_compose:
            .create("ul")  # :ref:menu_compose:
            .spawn(self.entries, "li")  # :ref:menu_compose:
            .each(  # :ref:menu_compose:
                lambda key, item: item.classes("menu-item")  # :ref:menu_compose:
                .create("a")  # :ref:menu_compose:
                .text(key)  # :ref:menu_compose:
                .attrs(href=self.entries[key])  # :ref:menu_compose:
            )  # :ref:menu_compose:
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

# ```html title="markup.py" linenums="65"
# ...
# :include:66:94:markup.html:
# ...
# ```

# The magic happens in two places. First, when we create the `Menu` instance,
# we pass the items as a mapping and store it in the instance.

# :hl:menu_constructor:

# And then in the `compose` method we simply build our markup as desired using
# the fluent API, the regular `add` method, the constructor syntax, etc.

# :hl:menu_compose:

# In case you didn't notice, instead of `spawn(len(self.entries), ...)` we invoked it
# as `spaw(self.entries, ...)`, that is, passing directly an iterator instead of a number.
# In this case, `violetear` will create one element for item in the iterator,
# and will associate the corresponding item with the element.
# Then, when you call `each` you'll get that item as the first parameter of your lambda function.

# ??? question "Aren't we missing a `root()`?"
#
#     If you think we're missing a `root()` call at the end of `compose`
#     then you're right, we should have it there because the return value
#     of that expression is the `ElementSet` composed of the menu items.
#
#     However, you will *always* end up calling `root()` at the end of
#     your compose because you're always creating a detached element.
#     Hence, in favour of DRYness, we will call `root()` for you
#     when this component gets rendered.

# Now, if this still looks a bit ugly to you, we can make it even better.
# Part of the problem is that the menu items are themselves another abstraction
# that we are using implicitly. Let's make it explicit.


class MenuItem(Component):
    def __init__(self, name, href) -> None:
        super().__init__()
        self.name = name
        self.href = href

    def compose(self, content) -> Element:
        return Element(
            "li", Element("a", text=self.name, href=self.href), classes="menu-item"
        )


# And then we can redefine our `Menu` class to strip away the item management.


class Menu(Component):
    def compose(self, content) -> Element:
        return (
            Element("div")
            .classes("menu")
            .create("ul")  # :ref:compose_content:
            .extend(content)  # :ref:compose_content:
        )


# On render time, `compose` will be called recursively on all children `Components`,
# so you can safely mix `Component`s and regular `Element`s and everything will work out just fine.

# Thus, now we  create the child elements of type `MenuItem` explicitly
# and make sure to inject them at the right location in the markup we build at `compose`,
# using the `content` parameter that we've been ignoring so far.

# :hl:compose_content:

# It doesn't seem like we've gained much with this pattern but now we have made our `Menu`
# abstraction fully compatible with the `Element` API, so we can do things like freely
# mixing `Menu` and `MenuItem` with regular `Element`s  for ultimate flexibility
# plus maximum expresivity.

# For example, here we design a menu with an explicit div with class `"divider"` in-between
# the actual menu items.

doc.body.add(
    Menu().extend(
        MenuItem("Home", "/"),
        MenuItem("Pricing", "/pricing"),
        MenuItem("Products", "/products"),
        Element("div", classes="divider"),  # :hl:
        MenuItem("About", "/about-us"),
    )
)

# > :information_source: The `extend` method just calls `add` for each item.

# And the generated HTML blends perfectly the markup generated from the `compose` methods
# with the explicit markup.

# ```html title="markup.html" linenums="94" hl_lines="19 20"
# ...
# :include:95:120:markup.html:
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


# Finally, both the `create` and `spawn` methods accept a `Component` derivative class instead
# of a tag name, in which case it will instantiate the passed class.

menu = doc.body.create(Menu)

# The advantage is that the type checker will infer `Menu` as the type for the variable `menu`,
# helping you in subsequent chained method calls.

if __name__ == "__main__":  # :skip:
    doc.render("markup.html")
