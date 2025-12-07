from pydantic import BaseModel
from violetear import App
from violetear.markup import Document, Element

app = App(title="RPC Demo")


# 1. Define a Shared Model (Optional, but good practice)
class UserData(BaseModel):
    name: str
    age: int


# 2. Define the Server Logic
@app.server
def create_user(name: str, age: int) -> UserData:
    # This runs on the SERVER.
    # Pydantic validation happens automatically here!
    print(f"Server: Creating user {name}, age {age}")

    # Return a model or dict. It will be serialized to JSON.
    return UserData(name=name.upper(), age=age)


# 3. Define the Client Logic
@app.client
async def on_submit(event):
    from js import document, alert

    # Get values from DOM
    name = document.getElementById("name-input").value
    age = int(document.getElementById("age-input").value)

    # Call the Server Stub!
    # This looks like a local call, but it does a fetch() under the hood.
    try:
        user = await create_user(name=name, age=age)
        alert(f"Server replied: Created user {user['name']}!")
    except Exception as e:
        alert(f"Error: {e}")


# 4. The UI
@app.route("/")
def index():
    doc = Document(title="RPC Demo")

    doc.body.extend(
        Element("h1", text="Server RPC Test"),
        Element("input", id="name-input", placeholder="Name"),
        Element("input", id="age-input", placeholder="Age", type="number"),
        Element("button", text="Create User").on("click", on_submit),
    )

    return doc


app.run()
