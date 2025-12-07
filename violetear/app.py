import os
import inspect
from pathlib import Path
from textwrap import dedent
from typing import Any, Callable, Dict, List, Union


# --- Optional Server Dependencies ---
try:
    from fastapi import FastAPI, APIRouter, Request, Response
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn

    HAS_SERVER = True
except ImportError:
    HAS_SERVER = False
    # Dummy classes for type hinting
    FastAPI = object  # type: ignore
    APIRouter = object  # type: ignore
    Request = object  # type: ignore
    Response = object  # type: ignore


from .stylesheet import StyleSheet
from .markup import Document, StyleResource


class App:
    """
    The main Violetear Application class.
    Wraps FastAPI to provide a full-stack Python web framework experience.
    """

    def __init__(self, title: str = "Violetear App"):
        if not HAS_SERVER:
            raise ImportError(
                "Violetear Server dependencies are missing. "
                "Please install them with: uv add --extra server 'fastapi[standard]'"
            )

        self.title = title
        self.api = FastAPI(title=title)

        # Registry of served styles to prevent duplicate route registration
        self.served_styles: Dict[str, StyleSheet] = {}

        # Registry for client-side functions
        self.client_functions: Dict[str, Callable] = {}

        # Register the Bundle Route (Dynamic Python file)
        @self.api.get("/_violetear/bundle.py")
        def get_bundle():
            return Response(content=self._generate_bundle(), media_type="text/x-python")

    def client(self, func: Callable):
        """Decorator to mark a function to be compiled to the client."""
        self.client_functions[func.__name__] = func
        return func

    def style(self, path: str, sheet: StyleSheet):
        """
        Registers a stylesheet to be served by the app at a specific path.

        Overrides any previous stylesheet at that path.
        """
        if path not in self.served_styles:
            # Register the route dynamically (just once)
            @self.api.get(path)
            def serve_css():
                # Render the full CSS content
                css_content = self.served_styles[path].render()
                return Response(content=css_content, media_type="text/css")

        # Set the stylesheet, overrides if existing
        # This means we can change stylesheets dynamically
        self.served_styles[path] = sheet

    def _register_document_styles(self, doc: Document):
        """
        Scans a Document for external stylesheets defined in Python
        and registers their routes on the fly.
        """
        for resource in doc.head.styles:
            if isinstance(resource, StyleResource):
                # If it has a sheet object AND a URL, it needs to be served
                if resource.sheet and resource.href and not resource.inline:
                    self.style(resource.href, resource.sheet)

    def _generate_bundle(self) -> str:
        """
        Generates the Python bundle to run in the browser.
        It combines the runtime logic + user functions.
        """
        # 1. Mock the 'app' object so decorators don't fail in the browser
        header = (
            "class MockApp:\n    def client(self, f): return f\n\napp = MockApp()\n\n"
        )

        # 2. Read the Client Runtime (Hydration logic)
        runtime_path = Path(__file__).parent / "client.py"

        with open(runtime_path, "r") as f:
            runtime_code = f.read()

        # 3. Extract User Functions
        user_code = []

        for name, func in self.client_functions.items():
            user_code.append(inspect.getsource(func))

        # 4. Initialization
        init_code = "\n\n# --- Init ---\n\nhydrate(globals())\n"

        return header + runtime_code + "\n\n" + "\n".join(user_code) + init_code

    def _inject_client_side(self, doc: Document):
        """Injects Pyodide and the Bundle bootstrapper."""
        # 1. Load Pyodide
        doc.script(src="https://cdn.jsdelivr.net/pyodide/v0.29.0/full/pyodide.js")

        # 2. Bootstrap Script
        bootstrap = dedent(
            """
        async function main() {
            let pyodide = await loadPyodide();
            let response = await fetch("/_violetear/bundle.py");
            let code = await response.text();
            await pyodide.runPythonAsync(code);
        }
        main();
        """
        )

        doc.script(content=bootstrap)

    def route(self, path: str, methods: List[str] = ["GET"]):
        """
        Decorator to register a route.
        """

        def decorator(func: Callable):
            @self.api.api_route(path, methods=methods)
            async def wrapper(request: Request):
                # 1. Handle Request (POST/GET)
                if request.method == "POST":
                    form_data = await request.form()
                    # Simple check if function accepts arguments
                    if inspect.signature(func).parameters:
                        response = func(form_data)
                    else:
                        response = func()
                else:
                    response = func()

                # Await if async
                if inspect.isawaitable(response):
                    response = await response

                # 2. Handle Document Rendering
                if isinstance(response, Document):
                    # Check if this doc uses any new stylesheets we need to serve
                    self._register_document_styles(response)

                    # Check if this document contains Python bindings
                    if response.body.has_bindings():
                        self._inject_client_side(response)

                    # Render the HTML (which will contain <link href="..."> tags)
                    return HTMLResponse(response.render())

                # 3. Return raw response (JSON, Dict, etc.)
                return response

            return wrapper

        return decorator

    def mount_static(self, directory: str, path: str = "/static"):
        """Mounts a static file directory."""
        if os.path.isdir(directory):
            self.api.mount(path, StaticFiles(directory=directory), name="static")

    def run(self, host="0.0.0.0", port=8000, **kwargs):
        """Helper to run via uvicorn programmatically."""
        uvicorn.run(self.api, host=host, port=port, **kwargs)
