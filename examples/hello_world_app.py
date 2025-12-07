# main.py
from violetear import App
from violetear.markup import Document, Element

app = App()


@app.route("/")
def index():
    doc = Document(title="Hello Violetear")
    doc.body.extend(
        Element("h1", text="Hello World!"),
        Element("p", text="Served via Violetear App Engine."),
    )
    return doc


if __name__ == "__main__":
    app.run()
