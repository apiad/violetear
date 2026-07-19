# Quickstart

This guide builds a fully interactive counter app — state persists via Local Storage, DOM updates instantly, server syncs in the background. **Zero JavaScript.**

## 1. Create the app

```python
from violetear import App, StyleSheet
from violetear.color import Colors
from violetear.markup import Document

app = App(title="Counter")
```

## 2. Define styles

```python
sheet = StyleSheet()
sheet.select("body").background(Colors.AliceBlue).font(family="sans-serif") \
     .flexbox(align="center", justify="center").height("100vh")
sheet.select(".card").background(Colors.White).padding(40).rounded(12).shadow()
sheet.select(".count").font(size=64, weight="bold").color(Colors.SlateBlue)
sheet.select("button").padding("10px 24px").rounded(8).border(0).rules(cursor="pointer")
sheet.select(".btn-plus").background(Colors.MediumSeaGreen).color(Colors.White)
sheet.select(".btn-minus").background(Colors.IndianRed).color(Colors.White)

app.style("/style.css", sheet)
```

## 3. Client-side state

```python
from dataclasses import dataclass
from violetear.js import DOM, Event, localStorage

@app.local
@dataclass
class State:
    count: int = 0
```

`@app.local` compiles this dataclass to a reactive JavaScript singleton. Assign a field — the DOM updates automatically.

## 4. Client functions

```python
@app.client.on("ready")
async def init():
    saved = localStorage.count
    if saved is not None:
        State.count = int(saved)

@app.client.callback
async def change(event: Event):
    action = event.target.dataset.action
    State.count = State.count + (1 if action == "plus" else -1)
    localStorage.count = State.count
    await report(count=State.count)
```

These functions are **compiled to JavaScript** at startup. Import browser APIs from `violetear.js` — they are type-correct Python stubs in the IDE and JS globals in the browser.

## 5. Server RPC

```python
@app.server.rpc
async def report(count: int):
    print(f"[server] count is now {count}")
```

## 6. Build the page

```python
from violetear.markup import Document

@app.view("/")
def index():
    doc = Document(title="Counter")
    doc.head.link_css("/style.css")

    with doc.body as body:
        with body.div(classes="card") as card:
            card.h2(text="Isomorphic Counter")
            card.div(id="display", classes="count").text(State.count)
            card.button(text="−", data_action="minus").onclick(change)
            card.button(text="+", data_action="plus").onclick(change)

    return doc

if __name__ == "__main__":
    app.run()
```

## Run it

```bash
python app.py
```

Open `http://localhost:8000`. Full-stack, styled, reactive — in ~50 lines of pure Python.

---

## Next steps

- [State management →](concepts/state.md) — `@app.local` vs `@app.shared`
- [Real-time shared state →](concepts/realtime.md) — multiplayer with `@app.shared`
- [Partials & DOM →](concepts/partials.md) — server-rendered fragments injected client-side
