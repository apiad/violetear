import os
import inspect
import hashlib
import json
from pathlib import Path
from textwrap import dedent
from typing import Any, Callable, Dict, List, Union
import uuid


# --- Optional Server Dependencies ---
try:
    from pydantic import create_model
    from fastapi import FastAPI, APIRouter, Request, Response
    from fastapi.responses import HTMLResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn

    HAS_SERVER = True

except ImportError:
    raise ImportError(
        "Violetear Server dependencies are missing. "
        "Please install them with: uv add --extra server 'fastapi[standard]'"
    )


from .stylesheet import StyleSheet
from .markup import Document, StyleResource
from .pwa import Manifest, ServiceWorker


class App:
    """
    The main Violetear Application class.
    Wraps FastAPI to provide a full-stack Python web framework experience.
    """

    def __init__(
        self,
        title: str = "Violetear App",
        favicon: str | None = None,
        fade_in: float = 0.1,
        version: str | None = None,
    ):
        self.title = title
        self.api = FastAPI(title=title)

        # Automatic Versioning Strategy:
        # If version is None, generate a random hash (Startup ID).
        # This ensures every server restart invalidates the cache.
        if version is None:
            self.version = uuid.uuid4().hex[:8]
        else:
            self.version = version

        if favicon is None:
            favicon = str(Path(__file__).parent / "icon.png")

        self.favicon = favicon
        self.fade_in = fade_in

        # Standard path for browser favicon requests
        @self.api.get("/favicon.ico", include_in_schema=False)
        async def get_favicon():
            return FileResponse(self.favicon)

        # Registry of served styles to prevent duplicate route registration
        self.served_styles: Dict[str, StyleSheet] = {}

        # Registry for client- and serverside functions
        self.client_functions: Dict[str, Callable] = {}
        self.server_functions: Dict[str, Callable] = {}

        # Names of client-side functions to run on load
        self.startup_functions: List[str] = []

        # PWA Registry: route_scope_hash -> (Manifest, ServiceWorker)
        self.pwa_registry: Dict[str, tuple[Manifest, ServiceWorker]] = {}

        # Register the Bundle Route (Dynamic Python file)
        @self.api.get("/_violetear/bundle.py")
        def get_bundle():
            return Response(content=self._generate_bundle(), media_type="text/x-python")

        # --- PWA Asset Routes ---
        @self.api.get("/_violetear/pwa/{scope_hash}/manifest.json")
        def get_manifest(scope_hash: str):
            if scope_hash not in self.pwa_registry:
                return Response(status_code=404)

            manifest, _ = self.pwa_registry[scope_hash]
            return Response(content=manifest.render(), media_type="application/json")

        @self.api.get("/_violetear/pwa/{scope_hash}/sw.js")
        def get_service_worker(scope_hash: str):
            if scope_hash not in self.pwa_registry:
                return Response(status_code=404)

            _, sw = self.pwa_registry[scope_hash]
            # Crucial: Allow this script to control pages at the route's scope
            # even though the script is served from /_violetear/...
            headers = {"Service-Worker-Allowed": "/"}
            return Response(
                content=sw.render(),
                media_type="application/javascript",
                headers=headers,
            )

    def client(self, func: Callable):
        """Decorator to mark a function to be compiled to the client."""
        if not inspect.iscoroutinefunction(func):
            raise ValueError("func must be async")

        self.client_functions[func.__name__] = func
        return func

    def startup(self, func: Callable):
        """
        Decorator to mark a function to run automatically when the client loads.
        Also registers it as a client function.
        """
        if not inspect.iscoroutinefunction(func):
            raise ValueError("func must be async")

        self.client(func)
        self.startup_functions.append(func.__name__)
        return func

    def server(self, func: Callable):
        """
        Decorator to expose a function as a server-side RPC endpoint.
        The client bundle will receive a stub that calls this endpoint via fetch.
        """
        if not inspect.iscoroutinefunction(func):
            raise ValueError("func must be async")

        self.server_functions[func.__name__] = func

        # 1. Introspect the function to find arguments
        sig = inspect.signature(func)
        fields = {}

        for name, param in sig.parameters.items():
            # Skip 'self' if it happens to be a method (though we expect functions)
            if name == "self":
                continue

            # Determine default value (required if empty)
            default = param.default

            if default is inspect.Parameter.empty:
                default = ...  # Ellipsis means field is required in Pydantic

            # Determine type annotation (default to Any if missing)
            annotation = param.annotation

            if annotation is inspect.Parameter.empty:
                annotation = Any

            fields[name] = (annotation, default)

        # 2. Create a dynamic Pydantic model representing the JSON Body
        # This tells FastAPI: "Expect a JSON body with these fields"
        BodyModel = create_model(f"{func.__name__}Request", **fields)

        # 3. Create a wrapper that accepts the Model
        # We need to handle both sync and async user functions

        async def wrapper(body: BodyModel):  # type: ignore
            return await func(**body.model_dump())

        # 4. Register the route with FastAPI using the wrapper
        route_path = f"/_violetear/rpc/{func.__name__}"
        self.api.post(route_path)(wrapper)

        return func

    def style(self, path: str, sheet: StyleSheet):
        """
        Registers a stylesheet to be served by the app at a specific path.

        Overrides any previous stylesheet at that path.
        """
        if path not in self.served_styles:
            # Register the route dynamically (just once)
            if not path.startswith("/"):
                path = f"/{path}"

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
            # If it has a sheet object AND a URL, it needs to be served
            if resource.sheet and resource.href and not resource.inline:
                self.style(resource.href, resource.sheet)

    def _generate_server_stubs(self) -> str:
        """
        Generates client-side Python stubs for server functions.
        These stubs use fetch() to call the RPC endpoints.
        """
        stubs = []

        for name, func in self.server_functions.items():
            # Introspect the function to support positional arguments in the stub
            sig = inspect.signature(func)
            arg_names = [p.name for p in sig.parameters.values()]

            # We generate a Python async function that wraps the fetch call
            stub = dedent(
                f"""
                async def {name}(*args, **kwargs):
                    import json
                    from pyodide.http import pyfetch

                    # Map positional args to their names (captured from server signature)
                    arg_names = {arg_names!r}
                    payload = {{k: v for k, v in zip(arg_names, args)}}
                    payload.update(kwargs)

                    # Perform RPC
                    response = await pyfetch(
                        "/_violetear/rpc/{name}",
                        method="POST",
                        headers={{"Content-Type": "application/json"}},
                        body=json.dumps(payload)
                    )

                    if not response.ok:
                        raise Exception(f"RPC Error: {{response.status}} {{response.statusText}}")

                    # Automatically convert JSON response back to Python objects (dicts/lists)
                    return await response.json()
                """
            )
            stubs.append(stub)

        return "\n\n".join(stubs)

    def _generate_bundle(self) -> str:
        """
        Generates the Python bundle to run in the browser.
        """
        # 1. Mock the 'app' object
        header = "class Event: pass"

        # 2. Inject violetear.dom module
        # This allows 'from violetear.dom import Document' to work in the browser
        dom_path = Path(__file__).parent / "dom.py"
        with open(dom_path, "r") as f:
            dom_source = f.read()

        dom_injection = dedent(
            f"""
            import sys, types
            # Create virtual module 'violetear'
            m_violetear = types.ModuleType("violetear")
            sys.modules["violetear"] = m_violetear

            # Create virtual module 'violetear.dom'
            m_dom = types.ModuleType("violetear.dom")
            sys.modules["violetear.dom"] = m_dom

            # Execute source
            exec({repr(dom_source)}, m_dom.__dict__)
            """
        )

        # Inject Storage
        storage_path = Path(__file__).parent / "storage.py"
        with open(storage_path, "r") as f:
            storage_source = f.read()

        storage_injection = dedent(
            f"""
            m_storage = types.ModuleType("violetear.storage")
            sys.modules["violetear.storage"] = m_storage
            exec({repr(storage_source)}, m_storage.__dict__)
            """
        )

        # 3. Read the Client Runtime (Hydration logic)
        runtime_path = Path(__file__).parent / "client.py"
        with open(runtime_path, "r") as f:
            runtime_code = f.read()

        # 4. Extract User Functions
        user_code = []
        for name, func in self.client_functions.items():
            code = inspect.getsource(func).split("\n")
            code = [c for c in code if not c.startswith("@")]  # remove decorators
            user_code.append("\n".join(code))

        # 5. Generate Server Stubs
        server_stubs = self._generate_server_stubs()

        # 6. Initialization
        init_code = "# --- Init ---\nhydrate(globals())"

        # Run startup functions
        for func_name in self.startup_functions:
            init_code += f"\nawait {func_name}()"

        return "\n\n".join(
            [
                header,
                dom_injection,
                storage_injection,
                runtime_code,
                "\n\n".join(user_code),
                server_stubs,
                init_code,
            ]
        )

    def _version_url(self, url: str) -> str:
        """Appends the app version to the URL to bust caches."""
        delimiter = "&" if "?" in url else "?"
        return f"{url}{delimiter}v={self.version}"

    def _inject_client_side(self, doc: Document):
        """Injects Pyodide and the Bundle bootstrapper."""

        if self.fade_in > 0:
            # 1. The "Cloak" Script
            # We inject this FIRST so it runs immediately before the body renders.
            # It creates a style that hides the body and disables clicking.
            cloak_script = dedent(
                """
                var cloak = document.createElement("style");
                cloak.id = "violetear-cloak";
                // opacity: 0 -> hides content visually
                // pointer-events: none -> prevents clicking on invisible buttons
                cloak.innerHTML = "body { opacity: 0; pointer-events: none; }";
                document.head.appendChild(cloak);
                """
            )
            doc.script(content=cloak_script)

        # 2. Load Pyodide (from CDN)
        doc.script(src="https://cdn.jsdelivr.net/pyodide/v0.29.0/full/pyodide.js")

        # 3. Bootstrap Script
        # We update this to remove the cloak once hydration is complete.
        # Ensure we fetch the versioned bundle to avoid stale logic
        bundle_url = self._version_url("/_violetear/bundle.py")

        bootstrap = dedent(
            f"""
            async function main() {{
                // optional: You could inject a 'Loading...' spinner here if you wanted

                let pyodide = await loadPyodide();
                let response = await fetch("{bundle_url}");
                let code = await response.text();
                await pyodide.runPythonAsync(code);

                // --- Hydration Complete ---

                // Find the cloak style
                let cloak = document.getElementById("violetear-cloak");
                if (cloak) {{
                    // Update styles to fade in
                    cloak.innerHTML = "body {{ opacity: 1; pointer-events: auto; transition: opacity {self.fade_in}s ease-in-out; }}";

                    // Clean up the style tag after the transition finishes
                    setTimeout(() => cloak.remove(), {int(self.fade_in * 1000)});
                }}
            }}

            await main();
            """
        )

        doc.script(content=bootstrap)

    def _register_pwa(self, path: str, config: Union[bool, Manifest]):
        """
        Registers a PWA configuration for a specific route path.
        """
        scope_hash = hashlib.md5(path.encode()).hexdigest()[:8]

        if isinstance(config, Manifest):
            manifest = config
            # Ensure the manifest scope matches the route if not explicitly set
            if manifest.scope == "/":
                manifest.scope = path
            if manifest.start_url == ".":
                manifest.start_url = path
        else:
            # Generate a default manifest
            manifest = Manifest(
                name=self.title,
                start_url=path,
                scope=path,
                display="standalone",
                background_color="#ffffff",
                theme_color="#ffffff",
            )

        # Create Service Worker
        sw = ServiceWorker(version=self.version)

        # Add basic assets to cache
        # We implicitly version these to ensure the SW caches fresh copies
        sw.add_assets(
            manifest.start_url,  # Nav request (HTML) - network first, but good to have in cache
            self._version_url("/_violetear/bundle.py"),
            self._version_url("/favicon.ico"),
        )

        self.pwa_registry[scope_hash] = (manifest, sw)

    def _inject_pwa_tags(self, doc: Document, path: str):
        """
        Injects the PWA manifest link and Service Worker registration script.
        Also patches the document's resources to use versioned URLs.
        """
        scope_hash = hashlib.md5(path.encode()).hexdigest()[:8]

        if scope_hash not in self.pwa_registry:
            return

        manifest_url = f"/_violetear/pwa/{scope_hash}/manifest.json"
        sw_url = f"/_violetear/pwa/{scope_hash}/sw.js"

        # 1. Inject Manifest Link (using JS as Document.Head doesn't support generic links yet)
        # Note: In a future update to Markup, we should support doc.head.add_link()
        js_injector = f"""
        var link = document.createElement('link');
        link.rel = 'manifest';
        link.href = '{manifest_url}';
        document.head.appendChild(link);
        """
        doc.script(content=js_injector)

        # 2. Inject Service Worker Registration
        sw_script = dedent(
            f"""
            if ('serviceWorker' in navigator) {{
                window.addEventListener('load', () => {{
                    navigator.serviceWorker.register('{sw_url}', {{ scope: '{path}' }})
                        .then(reg => console.log('[Violetear] SW registered for {path}', reg))
                        .catch(err => console.log('[Violetear] SW registration failed', err));
                }});
            }}
            """
        )
        doc.script(content=sw_script)

        # 3. Add styles and scripts to the SW cache
        # We also rewrite the document's resource URLs to include the version hash.
        # This ensures the HTML <link> matches the Cache Key in the Service Worker.
        _, sw = self.pwa_registry[scope_hash]

        for style in doc.head.styles:
            if style.href and not style.href.startswith(("http", "//")):
                style.href = self._version_url(style.href)
                sw.add_assets(style.href)

        for script in doc.head.scripts:
            if script.src and not script.src.startswith(("http", "//")):
                script.src = self._version_url(script.src)
                sw.add_assets(script.src)

    def route(
        self, path: str, methods: List[str] = ["GET"], pwa: bool | Manifest = False
    ):
        """
        Decorator to register a route.

        :param pwa: If True (or a Manifest object), enables PWA features for this route.
        """
        # Register PWA if requested
        if pwa:
            self._register_pwa(path, pwa)

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

                    # Inject PWA tags if enabled for this route
                    if pwa:
                        self._inject_pwa_tags(response, path)

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
