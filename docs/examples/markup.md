# Generating markup

This example will show you how to generate HTML markup completely on-the-fly from
Python code, using the classes from `violetear.markup`.
You can use this functionality to quickly create prototype markup to visualize or debug
your styles.

!!! note
    Even though `violetear` can render arbitrary HTML, this functionality is **not** intended
    to replace a proper template engine like Jinja.

    The functionality in `violetear.markup` is only intended to be used for prototyping and
    testing. `violetear` will never aim to become a production-ready HTML rendering engine.
    That being said, it is pretty cool!

## Basic setup

Everything starts from the `Document` class.
At this point you can define a title.



```python linenums="16" title="markup.py"
from violetear.markup import Element, Document
from violetear.stylesheet import StyleSheet

doc = Document(title="Example: Markup - violetear")
```

We can also add stylesheets to our page that will be rendered either inline or as separate files.



```python linenums="21" title="markup.py"
sheet = StyleSheet(normalize=True)

doc.style(sheet, inline=False, href="markup.css")
```

Just with this let's take a look at the resulting HTML file.

```html title="markup.html" linenums="1"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Example: Markup - violetear</title>
    <link rel="stylesheet" href="markup.css">
</head>
...
```

## Adding elements to the body

There are a couple ways to add elements to a page.
Let's start with the most basic ones.

You can manually create `Element` instances and add them to the body.



```python linenums="33" title="markup.py"
doc.body.add(Element("h1", classes=["title"], text="This is a header"))
```

Elements can have child elements.



```python linenums="35" title="markup.py"
doc.body.add(
    Element(
        "ul",
        Element("li", text="First item"),
        Element("li", text="Second item"),
        Element("li", text="Third item"),
    )
)
```

And you can add inline styles using the `Style` class, in all its fluent glory!



```python linenums="44" title="markup.py"
from violetear.style import Style
from violetear.color import Colors


doc.body.add(
    Element(
        "span",
        text="A styled text!",
        style=Style().font(14).color(Colors.Red),
    )
)
```

As you might expect, this is the HTML file you get.

```html title="markup.html" linenums="1"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Example: Markup - violetear</title>
    <link rel="stylesheet" href="markup.css">
</head>
<body>
    <h1 class="title">
        This is a header
    </h1>
    <ul>
        <li>
            First item
        </li>
        <li>
            Second item
        </li>
        <li>
            Third item
        </li>
    </ul>
    <span style="font-size: 14px; color: rgba(255,0,0,1.0)">
        A styled text!
    </span>
...
```

## Using the fluent API to add elements

And while this works, it is rather cumbersome. For this reason,
the `Element` class gives you a fluent interface with the `Element.create` method
which creates and adds a new child element, and returns it so you can chain additional
method calls such as styling options.

A common pattern is to chain `Style` method calls.

To stay in flow, we can use the `style` method that receives a callable to be applied
to the internal style, but returns the current element, so you can obtain a reference to
last element created for further method calls.

For example, we can create a div and style it.



```python linenums="70" hl_lines="2 3" title="markup.py"
ul = (
    doc.body.create("div")  
    .style(Style().margin("auto").width(max=768))  
    .create("ul")  
    .style(Style().padding(5, bottom=10))  
)

for i in range(5):  
    ul.create("li").text(f"The {i+1}th element!")  
```

Then chain another call to create a `ul` and style it:



```python linenums="70" hl_lines="4 5" title="markup.py"
ul = (
    doc.body.create("div")  
    .style(Style().margin("auto").width(max=768))  
    .create("ul")  
    .style(Style().padding(5, bottom=10))  
)

for i in range(5):  
    ul.create("li").text(f"The {i+1}th element!")  
```


And then we can just keep building from the `ul` element.



```python linenums="70" hl_lines="8 9" title="markup.py"
ul = (
    doc.body.create("div")  
    .style(Style().margin("auto").width(max=768))  
    .create("ul")  
    .style(Style().padding(5, bottom=10))  
)

for i in range(5):  
    ul.create("li").text(f"The {i+1}th element!")  
```


Take a look to the newly created tags.

```html title="markup.html" linenums="27"
...
    <div style="margin: auto; max-width: 768px">
        <ul style="padding: 5px; padding-bottom: 10px">
            <li>
                The 1th element!
            </li>
            <li>
                The 2th element!
            </li>
            <li>
                The 3th element!
            </li>
            <li>
                The 4th element!
            </li>
            <li>
                The 5th element!
            </li>
        </ul>
    </div>
...
```

But it gets better, we can achieve the same result as before without having
to break the flow, by using `spawn` to create multiple children.



```python linenums="91" hl_lines="5" title="markup.py"
div = (
    doc.body.create("div")
    .classes("container")
    .create("ul")
    .spawn(5, "li")  
    .each(
        lambda i, item: item.text(f"The {i+1}th element").style(  
            Style().color(Colors.Blue.shade(i / 5))  
        )  
    )
    .parent()  
    .style(Style().padding(5, bottom=10))  
    .parent()  
    .style(Style().margin("auto").width(max=768))  
)
```

The syntax is very similar to `create` except that it receives a number of items to create
along with the tag.

This method returns an `ElementSet` with all the created items.
The `each` method can be used to configure each individual item, receiving both
the item and its index.



```python linenums="91" hl_lines="7 8 9" title="markup.py"
div = (
    doc.body.create("div")
    .classes("container")
    .create("ul")
    .spawn(5, "li")  
    .each(
        lambda i, item: item.text(f"The {i+1}th element").style(  
            Style().color(Colors.Blue.shade(i / 5))  
        )  
    )
    .parent()  
    .style(Style().padding(5, bottom=10))  
    .parent()  
    .style(Style().margin("auto").width(max=768))  
)
```


After finishing styling the children, we need to call `parent` to jump back to the `ul`,
which we then proceed to style.



```python linenums="91" hl_lines="11 12" title="markup.py"
div = (
    doc.body.create("div")
    .classes("container")
    .create("ul")
    .spawn(5, "li")  
    .each(
        lambda i, item: item.text(f"The {i+1}th element").style(  
            Style().color(Colors.Blue.shade(i / 5))  
        )  
    )
    .parent()  
    .style(Style().padding(5, bottom=10))  
    .parent()  
    .style(Style().margin("auto").width(max=768))  
)
```


We can then use `parent` again to navigate up and continue chaining method calls,
for example, to style the first `div` element we created.



```python linenums="91" hl_lines="13 14" title="markup.py"
div = (
    doc.body.create("div")
    .classes("container")
    .create("ul")
    .spawn(5, "li")  
    .each(
        lambda i, item: item.text(f"The {i+1}th element").style(  
            Style().color(Colors.Blue.shade(i / 5))  
        )  
    )
    .parent()  
    .style(Style().padding(5, bottom=10))  
    .parent()  
    .style(Style().margin("auto").width(max=768))  
)
```


Notice how we went down the tree creating and then up the tree styling.
In the same way, we could have called `style` just after each `create`.

Here's the result.

```html title="markup.html" linenums="46"
...
    <div class="container" style="margin: auto; max-width: 768px">
        <ul style="padding: 5px; padding-bottom: 10px">
            <li style="color: rgba(0,0,0,1.0)">
                The 1th element
            </li>
            <li style="color: rgba(0,0,102,1.0)">
                The 2th element
            </li>
            <li style="color: rgba(0,0,204,1.0)">
                The 3th element
            </li>
            <li style="color: rgba(50,50,255,1.0)">
                The 4th element
            </li>
            <li style="color: rgba(153,153,255,1.0)">
                The 5th element
            </li>
        </ul>
    </div>
...
```

## Defining and using components

So far we've been using the basic API which lets you create any type of HTML element.
However, this API can quickly become repetitive as you add similar markup for similar concepts.
If you want to create custom abstractions, like a menu, which may consitst of several
markup elements (a `div` with a `ul` inside, several `span`s, etc.,),
things can easily become convoluted.

One simple solution is to encapsulate your custom markup logic in a function, something like:

```python
def menu(*items):
    return (
        Element("div")
        .create("ul")
        .spawn(len(items), "li")
        .each(lambda i, item: item.text(items[i]))
        .root()
    )
```

> :information_source: The `root` method returns the top-most element in a hierarchy, i.e., the `div` in this case.

And then use it like:

```python
doc.body.add(menu("Home", "Products", "Pricing", "Abouts"))
```

And while this works, it is unsatisfying because even though we encapsulated the concept of a menu,
we didn't *abstracted* it.
The minute we invoke the encapsulated functionality we lost the menu abstraction and
we are left with a regular `div` with an `ul` and a bunch of `li`s inside.

For example, if you want to add a new item to your menu after created, what can you do?
There is no real abstraction of a menu that you can reference and modify.
What you want, of course, is a `Menu` class that you can instantiate and add
to a `Document`, manipulate at your will, and only on render time
expand it into the actual markup elements.

We can achieve that by inheriting from the `Component` class.

<a name="ref:Menu"></a>

```python linenums="158" hl_lines="1 4" title="markup.py"
from violetear.markup import Component  


class Menu(Component):  
    def __init__(self, **entries: str) -> None:
        super().__init__()
        self.entries = dict(**entries)  

    def compose(self, content) -> Element:
        return (
            Element("div")  
            .classes("menu")  
            .create("ul")  
            .spawn(self.entries, "li")  
            .each(  
                lambda key, item: item.classes("menu-item")  
                .create("a")  
                .text(key)  
                .attrs(href=self.entries[key])  
            )  
        )
```

Which we can instantiate as usual and add to our document:



```python linenums="180" title="markup.py"
menu = Menu(
    Home="/",
    Products="/products",
    Pricing="/pricing",
    About="/about-us",
)

doc.body.add(menu)
```

But if we modify the menu before rendering, it will work.
We can manipulate the abstraction directly, not the underlying HTML markup that
only will exist at render time.



```python linenums="191" title="markup.py"
menu.entries["Services"] = "/services"
```

Here's the end result:

```html title="markup.py" linenums="65"
...
    <div class="menu">
        <ul>
            <li class="menu-item">
                <a href="/">
                    Home
                </a>
            </li>
            <li class="menu-item">
                <a href="/products">
                    Products
                </a>
            </li>
            <li class="menu-item">
                <a href="/pricing">
                    Pricing
                </a>
            </li>
            <li class="menu-item">
                <a href="/about-us">
                    About
                </a>
            </li>
            <li class="menu-item">
                <a href="/services">
                    Services
                </a>
            </li>
        </ul>
    </div>
...
```

The magic happens in two places. First, when we create the `Menu` instance,
we pass the items as a mapping and store it in the instance.

<a name="ref:Menu"></a>

```python linenums="158" hl_lines="7" title="markup.py"
from violetear.markup import Component  


class Menu(Component):  
    def __init__(self, **entries: str) -> None:
        super().__init__()
        self.entries = dict(**entries)  

    def compose(self, content) -> Element:
        return (
            Element("div")  
            .classes("menu")  
            .create("ul")  
            .spawn(self.entries, "li")  
            .each(  
                lambda key, item: item.classes("menu-item")  
                .create("a")  
                .text(key)  
                .attrs(href=self.entries[key])  
            )  
        )
```


And then in the `compose` method we simply build our markup as desired using
the fluent API, the regular `add` method, the constructor syntax, etc.

<a name="ref:Menu"></a>

```python linenums="158" hl_lines="11 12 13 14 15 16 17 18 19 20" title="markup.py"
from violetear.markup import Component  


class Menu(Component):  
    def __init__(self, **entries: str) -> None:
        super().__init__()
        self.entries = dict(**entries)  

    def compose(self, content) -> Element:
        return (
            Element("div")  
            .classes("menu")  
            .create("ul")  
            .spawn(self.entries, "li")  
            .each(  
                lambda key, item: item.classes("menu-item")  
                .create("a")  
                .text(key)  
                .attrs(href=self.entries[key])  
            )  
        )
```


In case you didn't notice, instead of `spawn(len(self.entries), ...)` we invoked it
as `spaw(self.entries, ...)`, that is, passing directly an iterator instead of a number.
In this case, `violetear` will create one element for item in the iterator,
and will associate the corresponding item with the element.
Then, when you call `each` you'll get that item as the first parameter of your lambda function.

??? question "Aren't we missing a `root()`?"

    If you think we're missing a `root()` call at the end of `compose`
    then you're right, we should have it there because the return value
    of that expression is the `ElementSet` composed of the menu items.

    However, you will *always* end up calling `root()` at the end of
    your compose because you're always creating a detached element.
    Hence, in favour of DRYness, we will call `root()` for you
    when this component gets rendered.

Now, if this still looks a bit ugly to you, we can make it even better.
Part of the problem is that the menu items are themselves another abstraction
that we are using implicitly. Let's make it explicit.

<a name="ref:MenuItem"></a>

```python linenums="222" title="markup.py"
class MenuItem(Component):
    def __init__(self, name, href) -> None:
        super().__init__()
        self.name = name
        self.href = href

    def compose(self, content) -> Element:
        return Element(
            "li", Element("a", text=self.name, href=self.href), classes="menu-item"
        )
```

And then we can redefine our `Menu` class to strip away the item management.

<a name="ref:Menu"></a>

```python linenums="233" title="markup.py"
class Menu(Component):
    def compose(self, content) -> Element:
        return (
            Element("div")
            .classes("menu")
            .create("ul")  
            .extend(content)  
        )
```

On render time, `compose` will be called recursively on all children `Components`,
so you can safely mix `Component`s and regular `Element`s and everything will work out just fine.

Thus, now we  create the child elements of type `MenuItem` explicitly
and make sure to inject them at the right location in the markup we build at `compose`,
using the `content` parameter that we've been ignoring so far.

<a name="ref:Menu"></a>

```python linenums="233" hl_lines="6 7" title="markup.py"
class Menu(Component):
    def compose(self, content) -> Element:
        return (
            Element("div")
            .classes("menu")
            .create("ul")  
            .extend(content)  
        )
```


It doesn't seem like we've gained much with this pattern but now we have made our `Menu`
abstraction fully compatible with the `Element` API, so we can do things like freely
mixing `Menu` and `MenuItem` with regular `Element`s  for ultimate flexibility
plus maximum expresivity.

For example, here we design a menu with an explicit div with class `"divider"` in-between
the actual menu items.



```python linenums="253" hl_lines="6" title="markup.py"
doc.body.add(
    Menu().extend(
        MenuItem("Home", "/"),
        MenuItem("Pricing", "/pricing"),
        MenuItem("Products", "/products"),
        Element("div", classes="divider"),  
        MenuItem("About", "/about-us"),
    )
)
```

> :information_source: The `extend` method just calls `add` for each item.

And the generated HTML blends perfectly the markup generated from the `compose` methods
with the explicit markup.

```html title="markup.html" linenums="94" hl_lines="19 20"
...
    <div class="menu">
        <ul>
            <li class="menu-item">
                <a href="/">
                    Home
                </a>
            </li>
            <li class="menu-item">
                <a href="/pricing">
                    Pricing
                </a>
            </li>
            <li class="menu-item">
                <a href="/products">
                    Products
                </a>
            </li>
            <div class="divider">
            </div>
            <li class="menu-item">
                <a href="/about-us">
                    About
                </a>
            </li>
        </ul>
    </div>
...
```

??? note "Unopinionated to its core"
    Remember that `violetear` is totally unopinionated.
    We will never dictate how you have to structure your HTML or CSS.
    We simply give you the tools to build whatever abstraction you prefer.

    If you want to hack a simple HTML over a weekend you can use the fluent API
    and get away with it.
    If you're building something durable enough to deserve a complete design
    system with custom components, `violetear` can help you there as well.

Finally, both the `create` and `spawn` methods accept a `Component` derivative class instead
of a tag name, in which case it will instantiate the passed class.



```python linenums="281" title="markup.py"
menu = doc.body.create(Menu)
```

The advantage is that the type checker will infer `Menu` as the type for the variable `menu`,
helping you in subsequent chained method calls.

