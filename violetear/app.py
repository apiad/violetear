import asyncio
from contextlib import asynccontextmanager
import functools
import os
import inspect
import hashlib
import json
from pathlib import Path
from textwrap import dedent
from typing import Any, Callable, Dict, List, Set, Union
import uuid

from .stylesheet import StyleSheet
from .markup import Document, StyleResource
from .pwa import Manifest, ServiceWorker


# --- Optional Server Dependencies ---
try:
    from pydantic import create_model
    from fastapi import FastAPI, Request, Response
    from fastapi.responses import HTMLResponse, FileResponse
    from fastapi import WebSocket, WebSocketDisconnect

    import uvicorn

    HAS_SERVER = True

except ImportError:
    raise ImportError(
        "Violetear Server dependencies are missing. "
        "Please install them with: uv add --extra server 'fastapi[standard]'"
    )


class ServerRegistry:
    """
    Registry for Server-Side Logic (RPC, Realtime, Events).
    """

    def __init__(self, app: "App"):
        self.app = app
        self.rpc_functions: Dict[str, Callable] = {}
        self.realtime_functions: Dict[str, Callable] = {}
        self.event_handlers: Dict[str, List[Callable]] = {}

    def rpc(self, func: Callable):
        """
        Decorator for functions exposed to the client via HTTP (Fetch).
        The client awaits the result.
        """
        if not inspect.iscoroutinefunction(func):
            raise ValueError(f"RPC function '{func.__name__}' must be async")

        self.rpc_functions[func.__name__] = func

        # Delegate the actual FastAPI route generation to the App
        self.app._register_rpc_route(func)

        return func

    def realtime(self, func: Callable):
        """
        Decorator for functions exposed to the client via WebSocket.
        Fire-and-forget.
        """
        if not inspect.iscoroutinefunction(func):
            raise ValueError(f"Realtime function '{func.__name__}' must be async")

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            if result is not None:
                print(
                    f"⚠️ [Violetear] Warning: Realtime function '{func.__name__}' returned a value, but the client will not receive it."
                )

            return result

        # Preserve identity
        self.realtime_functions[func.__name__] = wrapper
        return wrapper

    def on(self, event: str):
        """
        Decorator for event handlers (e.g., 'connect', 'disconnect', 'custom_event').
        """

        def decorator(func: Callable):
            if not inspect.iscoroutinefunction(func):
                raise ValueError(f"Event handler '{func.__name__}' must be async")

            if event not in self.event_handlers:
                self.event_handlers[event] = []

            self.event_handlers[event].append(func)
            return func

        return decorator


class ClientFunctionStub:
    """
    Wraps a client-side function to prevent execution on the server.
    """

    def __init__(self, func: Callable, is_callback: bool = False):
        self.func = func
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__

        if is_callback:
            self.__is_violetear_callback__ = True

    def __call__(self, *args, **kwargs):
        raise RuntimeError(
            f"❌ Client function '{self.__name__}' cannot be called from the Server.\n"
            "It is meant to run in the Browser."
        )

    def __repr__(self):
        try:
            self.__is_violetear_callback__
            return f"<client.callback:{self.__name__})>"
        except:
            return f"<client:{self.__name__})>"


class ClientRealtimeStub(ClientFunctionStub):
    """
    Wraps a client-side realtime function to allow Server -> Client RPC.
    """

    def __init__(self, func: Callable, app: "App"):
        super().__init__(func)
        self.app = app

    async def broadcast(self, *args, **kwargs):
        """
        Triggers this function on ALL connected clients.
        """
        # Note: socket_manager must be initialized on the app
        await self.app.socket_manager.broadcast(self.__name__, args, kwargs)

    async def invoke(self, client_id: str, *args, **kwargs):
        """
        Triggers this function on a SPECIFIC client.
        """
        await self.app.socket_manager.invoke(client_id, self.__name__, args, kwargs)

    def __repr__(self):
        return f"<client.realtime:{self.__name__})>"


class ClientRegistry:
    """
    Registry for Client-Side Logic.
    """

    def __init__(self, app: "App"):
        self.app = app
        self.code_functions: Dict[str, Callable] = {}
        self.callback_names: Set[str] = set()
        self.realtime_functions: Dict[str, Callable] = {}
        self.event_handlers: Dict[str, List[str]] = {}

    def _register(self, func: Callable):
        """Helper to register the raw function source."""
        # Unwrap if it's already a stub (in case of decorator stacking)
        if isinstance(func, ClientFunctionStub):
            func = func.func

        if not inspect.iscoroutinefunction(func):
            raise ValueError(f"Client function '{func.__name__}' must be async")

        self.code_functions[func.__name__] = func
        return func

    def __call__(self, func: Callable):
        """
        Base Decorator: @app.client
        Marks a function to be transpiled to the browser.
        """
        func = self._register(func)
        return ClientFunctionStub(func)

    def callback(self, func: Callable):
        """
        Decorator: @app.client.callback
        Marks a function as safe to attach to DOM events.
        """
        func = self._register(func)
        self.callback_names.add(func.__name__)
        return ClientFunctionStub(func, is_callback=True)

    def realtime(self, func: Callable):
        """
        Decorator: @app.client.realtime
        Marks a function as invokable by the server.
        Returns a wrapper with .invoke() and .broadcast() methods.
        """
        func = self._register(func)
        self.realtime_functions[func.__name__] = func
        return ClientRealtimeStub(func, self.app)

    def on(self, event: str):
        """
        Decorator: @app.client.on("event_name")
        Registers a client-side event handler.
        """

        def decorator(func: Callable):
            func = self._register(func)

            if event not in self.event_handlers:
                self.event_handlers[event] = []

            self.event_handlers[event].append(func.__name__)

            return ClientFunctionStub(func)

        return decorator


class SocketManager:
    def __init__(self, app: "App"):
        # Keep track of active connections
        self.active_connections: dict[str, WebSocket] = {}
        self.app = app

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        await self.app.emit("connect", client_id)

    async def disconnect(self, client_id: str):
        self.active_connections.pop(client_id)
        await self.app.emit("disconnect", client_id)

    async def broadcast(self, func_name: str, args: tuple, kwargs: dict):
        """
        Sends a command to all connected clients to run a specific function.
        """
        payload = json.dumps(
            {"type": "rpc", "func": func_name, "args": args, "kwargs": kwargs}
        )

        # Iterate over all connections and send the message
        # We use a copy of the list to avoid modification errors during iteration
        for client_id, connection in list(self.active_connections.items()):
            try:
                await connection.send_text(payload)
            except Exception:
                # If sending fails (e.g. client disconnected), remove it
                await self.disconnect(client_id)

    async def invoke(self, client_id: str, func_name: str, args: tuple, kwargs: dict):
        """
        Sends a command to a specific client to run a specific function.
        """
        payload = json.dumps(
            {"type": "rpc", "func": func_name, "args": args, "kwargs": kwargs}
        )

        if not client_id in self.active_connections:
            raise KeyError("Invalid client id. Did it disconnect?")

        connection = self.active_connections[client_id]

        try:
            await connection.send_text(payload)
        except Exception:
            # If sending fails (e.g. client disconnected), remove it
            await self.disconnect(client_id)


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

        if version is None:
            self.version = uuid.uuid4().hex[:8]
        else:
            self.version = version

        if favicon is None:
            favicon = str(Path(__file__).parent / "icon.png")

        self.favicon = favicon
        self.fade_in = fade_in

        @asynccontextmanager
        async def lifespan(api: FastAPI):
            await self.emit("startup")
            yield
            await self.emit("shutdown")

        self.api = FastAPI(title=title, version=self.version, lifespan=lifespan)

        # Standard path for browser favicon requests
        @self.api.get("/favicon.ico", include_in_schema=False)
        async def get_favicon():
            return FileResponse(self.favicon)

        # Registry of served styles to prevent duplicate route registration
        self.served_styles: Dict[str, StyleSheet] = {}

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

        # In App.__init__
        self.socket_manager = SocketManager(self)

        @self.api.websocket("/_violetear/ws")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            await self.socket_manager.connect(client_id, websocket)
            try:
                while True:
                    # Listen for messages from the client
                    message = await websocket.receive_text()

                    try:
                        data = json.loads(message)
                    except json.JSONDecodeError:
                        print(f"[Violetear] ⚠️ Received invalid JSON from client {client_id}")
                        continue

                    # Dispatch 'realtime' function calls
                    if data.get("type") == "realtime":
                        func_name = data.get("func")
                        args = data.get("args", [])
                        kwargs = data.get("kwargs", {})

                        if func_name in self.server.realtime_functions:
                            func = self.server.realtime_functions[func_name]

                            # Execute the function (Fire-and-forget from client perspective)
                            # We await it here so the server processes it safely within this connection's loop
                            try:
                                await func(*args, **kwargs)
                            except Exception as e:
                                print(f"[Violetear] ❌ Error executing realtime function '{func_name}': {e}")
                        else:
                            print(f"[Violetear] ⚠️ Warning: Client {client_id} tried to call unknown realtime function '{func_name}'")

            except (WebSocketDisconnect, RuntimeError):
                await self.socket_manager.disconnect(client_id)

        # Client and Server registries
        self.client = ClientRegistry(self)
        self.server = ServerRegistry(self)

    def _register_rpc_route(self, func: Callable):
        """
        Decorator to expose a function as a server-side RPC endpoint.
        The client bundle will receive a stub that calls this endpoint via fetch.
        """
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
        These stubs delegate to the helper functions in client.py.
        """
        stubs = []

        # 1. RPC Stubs (HTTP POST)
        # These call the server and await a response.
        for name, func in self.server.rpc_functions.items():
            sig = inspect.signature(func)
            arg_names = [p.name for p in sig.parameters.values()]

            stub = dedent(
                f"""
                async def {name}(*args, **kwargs):
                    arg_names = {arg_names!r}
                    return await _call_rpc("{name}", arg_names, args, kwargs)
                """
            )
            stubs.append(stub)

        # 2. Realtime Stubs (WebSocket)
        # These send a fire-and-forget message.
        for name, func in self.server.realtime_functions.items():
            # Realtime functions don't need arg mapping on the client side
            # because they just forward *args directly to the socket payload.
            stub = dedent(
                f"""
                async def {name}(*args, **kwargs):
                    return await _call_realtime("{name}", args, kwargs)
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
        for name, func in self.client.code_functions.items():
            code = inspect.getsource(func).split("\n")
            code = [c for c in code if not c.startswith("@")]  # remove decorators
            user_code.append("\n".join(code))

        # --- SAFETY INJECTION START ---
        # We attach a dummy .broadcast() method to client functions running in the browser.
        # This prevents confusion if a user tries to call await my_func.broadcast() in client code.
        safety_checks = []
        safety_checks.append(
            dedent(
                """
                def _server_only_broadcast(*args, **kwargs):
                    raise RuntimeError("❌ .broadcast() cannot be called from the Client (Browser).\\nIt must be called from the Server to trigger client updates.")
                def _server_only_invoke(*args, **kwargs):
                    raise RuntimeError("❌ .invoke() cannot be called from the Client (Browser).\\nIt must be called from the Server to trigger client updates.")
                """
            )
        )

        for name in self.client.realtime_functions.keys():
            safety_checks.append(f"{name}.broadcast = _server_only_broadcast")
            safety_checks.append(f"{name}.invoke = _server_only_invoke")

        safety_code = "\n".join(safety_checks)
        # --- SAFETY INJECTION END ---

        # 5. Generate Server Stubs
        server_stubs = self._generate_server_stubs()

        # 6. Initialization
        init_code = "# --- Init ---\nhydrate(globals())"

        # Run startup functions
        for func_name in self.client.event_handlers.get("ready", []):
            init_code += f"\nawait {func_name}()"

        return "\n\n".join(
            [
                header,
                dom_injection,
                storage_injection,
                runtime_code,
                "\n\n".join(user_code),
                safety_code,
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

            main();
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

    async def emit(self, event: str, *args, **kwargs):
        """
        Emits a custom event on the server, invoking
        callbacks registered with @app.server.on(event).
        """
        handlers = [
            c(*args, **kwargs) for c in self.server.event_handlers.get(event, [])
        ]

        if handlers:
            await asyncio.gather(*handlers)

    def view(self, path: str, pwa: bool | Manifest = False):
        """
        Decorator to register a route.

        :param pwa: If True (or a Manifest object), enables PWA features for this route.
        """
        # Register PWA if requested
        if pwa:
            self._register_pwa(path, pwa)

        def decorator(func: Callable[[], str | Document]):
            @self.api.get(path)
            async def wrapper(request: Request):
                # 1. Handle Request (POST/GET)
                doc = func()

                # 2. Handle Document Rendering
                if isinstance(doc, Document):
                    # Check if this doc uses any new stylesheets we need to serve
                    self._register_document_styles(doc)

                    # Check if this document contains Python bindings
                    if self.client.code_functions:
                        self._inject_client_side(doc)

                    # Inject PWA tags if enabled for this route
                    if pwa:
                        self._inject_pwa_tags(doc, path)

                    # Render the HTML (which will contain <link href="..."> tags)
                    return HTMLResponse(doc.render())

                else:
                    return HTMLResponse(doc)

            return wrapper

        return decorator

    def run(self, host="0.0.0.0", port=8000, **kwargs):
        """Helper to run via uvicorn programmatically."""
        uvicorn.run(self.api, host=host, port=port, **kwargs)
