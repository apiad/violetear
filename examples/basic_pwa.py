# examples/auto_pwa.py
from violetear import App, Document, HTML

# Default behavior: version is random on every restart
app = App(title="Auto Updating PWA")

print(app.version)


@app.route("/", pwa=True)
def index():
    doc = Document(title=f"Auto PWA")
    doc.body.extend(
        HTML.h1(text="I update automatically!"),
        HTML.p(text="Restart the server and I will refresh."),
        HTML.p(text=f"Version: {app.version}"),
    )
    return doc


if __name__ == "__main__":
    app.run()
