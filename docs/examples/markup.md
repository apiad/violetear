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

Everything starts from the `Page` class.
At this point you can define a title.



```python linenums="16" title="markup.py"
from violetear.color import Colors
from violetear.markup import Element, Page
from violetear.style import Style
from violetear.stylesheet import StyleSheet

page = Page(title="Example: Markup - violetear")
```

We can also add stylesheets to our page that will be rendered either inline or as separate files.



```python linenums="23" title="markup.py"
sheet = StyleSheet(normalize=True)

page.style(sheet, inline=False, name="markup.css")

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



```python linenums="38" title="markup.py"
page.body.add(Element("h1", classes=["title"], text="This is a header"))
```

Elements can have child elements.



```python linenums="40" title="markup.py"
page.body.add(
    Element(
        "ul",
        Element("li", text="First item"),
        Element("li", text="Second item"),
        Element("li", text="Third item"),
    )
)
```

And you can add inline styles using the `Style` class, in all its fluent glory!



```python linenums="49" title="markup.py"
page.body.add(
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



```python linenums="70" title="markup.py"
page.body.create("div", "container", id="main").style.margin("auto").width(max=768)
```

However, this pattern breaks the fluent API because it returns the `Style` instance.
To stay in flow, we can use the `styled` method that receives a callable to be applied
to the internal style, but returns the current element, so you can obtain a reference to
last element created for further method calls.

For example, we can create a div and style it.



```python linenums="76" hl_lines="2 3" title="markup.py"
ul = (
    page.body.create("div", "container fluid")  
    .styled(lambda s: s.margin("auto").width(max=768))  
    .create("ul")  
    .styled(lambda s: s.padding(5, bottom=10))  
)

for i in range(5):  
    ul.create("li", text=f"The {i+1}th element!")  
```

Then chain another call to create a `ul` and style it:



```python linenums="76" hl_lines="4 5" title="markup.py"
ul = (
    page.body.create("div", "container fluid")  
    .styled(lambda s: s.margin("auto").width(max=768))  
    .create("ul")  
    .styled(lambda s: s.padding(5, bottom=10))  
)

for i in range(5):  
    ul.create("li", text=f"The {i+1}th element!")  
```


And then we can just keep building from the `ul` element.



```python linenums="76" hl_lines="8 9" title="markup.py"
ul = (
    page.body.create("div", "container fluid")  
    .styled(lambda s: s.margin("auto").width(max=768))  
    .create("ul")  
    .styled(lambda s: s.padding(5, bottom=10))  
)

for i in range(5):  
    ul.create("li", text=f"The {i+1}th element!")  
```


Take a look to the newly created tags.

```html title="markup.html" linenums="29"
...
    <div class="container fluid" style="margin: auto; max-width: 768px">
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



```python linenums="99" hl_lines="6" title="markup.py"
div = (
    page.body.create("div", "container")
    .styled(lambda s: s.margin("auto").width(max=768))
    .create("ul")
    .styled(lambda s: s.padding(5, bottom=10))
    .spawn(  
        5,  
        "li",  
        classes="item", 
        text=lambda i: f"The {i+1}th element", 
        style=lambda i: Style().color(Colors.Blue.shade(i / 5)), 
    )
    .parent() 
)
```

The syntax is very similar to `create` except that it receives a number of items to create
along with the tag.



```python linenums="99" hl_lines="7 8" title="markup.py"
div = (
    page.body.create("div", "container")
    .styled(lambda s: s.margin("auto").width(max=768))
    .create("ul")
    .styled(lambda s: s.padding(5, bottom=10))
    .spawn(  
        5,  
        "li",  
        classes="item", 
        text=lambda i: f"The {i+1}th element", 
        style=lambda i: Style().color(Colors.Blue.shade(i / 5)), 
    )
    .parent() 
)
```


And you can pass either direct values or callables to compute the values for the children attributes.



```python linenums="99" hl_lines="9 10 11" title="markup.py"
div = (
    page.body.create("div", "container")
    .styled(lambda s: s.margin("auto").width(max=768))
    .create("ul")
    .styled(lambda s: s.padding(5, bottom=10))
    .spawn(  
        5,  
        "li",  
        classes="item", 
        text=lambda i: f"The {i+1}th element", 
        style=lambda i: Style().color(Colors.Blue.shade(i / 5)), 
    )
    .parent() 
)
```


Finally, contrary to the `create` method which returns the newly created element,
the `spawn` method returns the same element on which you call it, in this case, the `ul`.
We can then use `parent` to navigate up and continue chaining method calls.



```python linenums="99" hl_lines="13" title="markup.py"
div = (
    page.body.create("div", "container")
    .styled(lambda s: s.margin("auto").width(max=768))
    .create("ul")
    .styled(lambda s: s.padding(5, bottom=10))
    .spawn(  
        5,  
        "li",  
        classes="item", 
        text=lambda i: f"The {i+1}th element", 
        style=lambda i: Style().color(Colors.Blue.shade(i / 5)), 
    )
    .parent() 
)
```


So here's the result.

```html title="markup.html" linenums="48"
...
    <div class="container" style="margin: auto; max-width: 768px">
        <ul style="padding: 5px; padding-bottom: 10px">
            <li class="item" style="color: rgba(0,0,0,1.0)">
                The 1th element
            </li>
            <li class="item" style="color: rgba(0,0,102,1.0)">
                The 2th element
            </li>
            <li class="item" style="color: rgba(0,0,204,1.0)">
                The 3th element
            </li>
            <li class="item" style="color: rgba(50,50,255,1.0)">
                The 4th element
            </li>
            <li class="item" style="color: rgba(153,153,255,1.0)">
                The 5th element
            </li>
        </ul>
    </div>
...
```

