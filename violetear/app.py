import ast
import asyncio
from contextlib import asynccontextmanager
import functools
import inspect
import hashlib
import json
from pathlib import Path
import textwrap
import traceback
from typing import Any, Callable, Dict, List, Union
import uuid

from .stylesheet import StyleSheet
from .markup import Document
from .pwa import Manifest, ServiceWorker
from .state import local
from .transpile import transpile_class, transpile_function, ClientCompileError
from .validate import signature_to_model, js_check_spec

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
        # name -> pydantic model for inbound client->server realtime validation
        self._realtime_validators: dict[str, type] = {}

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
        self._realtime_validators[func.__name__] = signature_to_model(
            func, f"{func.__name__}InKwargs"
        )
        return wrapper

    def _validate_incoming(self, func_name: str, args: list, kwargs: dict):
        """Validate an inbound client→server realtime payload against the
        handler signature. Binds positional args to param names (skipping
        client_id) so both the kwargs and positional forms validate. Raises
        pydantic.ValidationError on mismatch; no-op if no model registered."""
        model = self._realtime_validators.get(func_name)
        if model is None:
            return
        func = self.realtime_functions[func_name]
        params = [
            p
            for p in inspect.signature(inspect.unwrap(func)).parameters
            if p != "client_id"
        ]
        merged = dict(kwargs)
        for name, val in zip(params, args):
            merged[name] = val
        model(**merged)

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


def _wrap_realtime_params(fn_name: str, params: list[str], body: str) -> str:
    """Wrap realtime function to accept a kwargs object from the WS runtime."""
    # Original: async function receive_message(msg) { ... }
    # Wrapped:  async function receive_message({msg}) { ... }
    if not params:
        return f"async function {fn_name}() {{\n{body}\n}}"
    destructured = ", ".join(params)
    return f"async function {fn_name}({{{destructured}}}) {{\n{body}\n}}"


class ClientRegistry:
    """
    Registry for Client-Side Logic.
    """

    def __init__(self, app: "App"):
        self._app = app
        self._compiled_classes: dict[str, str] = {}
        # func_name -> (decorator_kind, js_source)
        # decorator_kind: "callback" | "realtime" | "on:<event>" | "client"
        self._compiled_functions: dict[str, tuple[str, str]] = {}
        self._lifecycle: dict[str, list[str]] = {}  # event -> [fn_name, ...]
        # name -> pydantic model (server-side outgoing validation)
        self._realtime_validators: dict[str, type] = {}
        # name -> JS check-spec string (client-side inbound validation)
        self._realtime_check_specs: dict[str, str] = {}

    def _register(self, func: Callable):
        """Helper to validate and compile the function to JS."""
        if isinstance(func, ClientFunctionStub):
            func = func.func

        if not inspect.iscoroutinefunction(func):
            raise ValueError(f"Client function '{func.__name__}' must be async")

        return func

    def __call__(self, func: Callable):
        """
        Base Decorator: @app.client
        Marks a function to be transpiled to the browser.
        """
        func = self._register(func)
        js = transpile_function(func)
        self._compiled_functions[func.__name__] = ("client", js)
        return ClientFunctionStub(func)

    def callback(self, func: Callable):
        """
        Decorator: @app.client.callback
        Marks a function as safe to attach to DOM events.
        """
        func = self._register(func)
        js = transpile_function(func)
        self._compiled_functions[func.__name__] = ("callback", js)
        return ClientFunctionStub(func, is_callback=True)

    def realtime(self, func: Callable):
        """
        Decorator: @app.client.realtime
        Marks a function as invokable by the server.
        Returns a wrapper with .invoke() and .broadcast() methods.
        """
        func = self._register(func)
        # Compile to JS then rewrite the param list for destructured kwargs
        raw_js = transpile_function(func)
        # Extract params and body from the compiled output to rewrap
        src = textwrap.dedent(inspect.getsource(func))
        tree = ast.parse(src)
        func_def = tree.body[0]
        params = [a.arg for a in func_def.args.args]
        # Split raw_js: first line is "async function name(params) {"
        # body is everything between first { and last }
        lines = raw_js.split("\n")
        # body lines are lines[1:-1]
        body = "\n".join(lines[1:-1])
        js = _wrap_realtime_params(func.__name__, params, body)
        self._compiled_functions[func.__name__] = ("realtime", js)
        # Derive both validators from the one signature (spec issue #8).
        self._realtime_validators[func.__name__] = signature_to_model(
            func, f"{func.__name__}Kwargs"
        )
        self._realtime_check_specs[func.__name__] = js_check_spec(func)
        return ClientRealtimeStub(func, self._app)

    def on(self, event: str):
        """
        Decorator: @app.client.on("event_name")
        Registers a client-side event handler.
        """

        def decorator(func: Callable):
            func = self._register(func)
            js = transpile_function(func)
            self._compiled_functions[func.__name__] = ("on:" + event, js)
            self._lifecycle.setdefault(event, []).append(func.__name__)
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

    def _validate_outgoing(self, func_name: str, kwargs: dict):
        """Validate server->client realtime kwargs against the handler signature.

        Raises pydantic.ValidationError before the frame is serialized/sent.
        No model registered (e.g. untyped handler) -> no-op.
        """
        model = self.app.client._realtime_validators.get(func_name)
        if model is not None:
            model(**kwargs)

    async def broadcast(self, func_name: str, args: tuple, kwargs: dict):
        """
        Sends a command to all connected clients to run a specific function.
        """
        self._validate_outgoing(func_name, kwargs)
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
        self._validate_outgoing(func_name, kwargs)
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
        storage_prefix: str = "",
    ):
        self.title = title
        self.storage_prefix = storage_prefix

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

        # Serve static runtime.js
        _runtime_js_path = Path(__file__).parent / "runtime.js"

        @self.api.get("/_violetear/runtime.js")
        def get_runtime():
            return Response(
                content=_runtime_js_path.read_text(encoding="utf-8"),
                media_type="application/javascript",
                headers={"Cache-Control": "public, max-age=3600"},
            )

        @self.api.get("/_violetear/bundle.js")
        def get_bundle():
            return Response(
                content=self._generate_bundle_js(),
                media_type="application/javascript",
            )

        # Registry of served styles to prevent duplicate route registration
        self.served_styles: Dict[str, StyleSheet] = {}

        # PWA Registry: route_scope_hash -> (Manifest, ServiceWorker)
        self.pwa_registry: Dict[str, tuple[Manifest, ServiceWorker]] = {}

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
                        print(
                            f"[Violetear] ⚠️ Received invalid JSON from client {client_id}"
                        )
                        continue

                    # Dispatch 'realtime' function calls
                    if data.get("type") == "realtime":
                        func_name = data.get("func")
                        args = data.get("args", [])
                        kwargs = data.get("kwargs", {})

                        if func_name in self.server.realtime_functions:
                            func = self.server.realtime_functions[func_name]

                            # Validate the inbound payload against the handler
                            # signature before running it (security-relevant trust
                            # boundary). Reject-and-skip: log, drop the frame, keep
                            # the connection open.
                            try:
                                self.server._validate_incoming(func_name, args, kwargs)
                            except Exception as _ve:
                                print(
                                    f"[Violetear] ⚠️ Rejected invalid inbound realtime "
                                    f"'{func_name}': {_ve}"
                                )
                                continue

                            # Execute the function (Fire-and-forget from client perspective)
                            # We await it here so the server processes it safely within this connection's loop
                            try:
                                # Inject client_id if the handler expects it as its
                                # first param. Inspect the UNDERLYING handler, not the
                                # @realtime wrapper's (*args, **kwargs) signature —
                                # functools.wraps makes inspect.signature follow
                                # __wrapped__ transparently, so unwrap explicitly to
                                # keep this decision deterministic.
                                target = inspect.unwrap(func)
                                param_names = list(
                                    inspect.signature(target).parameters.keys()
                                )
                                if param_names and param_names[0] == "client_id":
                                    # The connection owns the trusted client_id; drop
                                    # any client-supplied one so it's bound exactly
                                    # once (else: TypeError, multiple values).
                                    kwargs.pop("client_id", None)
                                    await func(client_id, *args, **kwargs)
                                else:
                                    await func(*args, **kwargs)
                            except Exception:
                                # Surface handler errors loudly: a swallowed exception
                                # here means the handler's broadcast/invoke never fires
                                # and a client blocked on the reply hangs forever.
                                print(
                                    f"[Violetear] ❌ Error executing realtime function '{func_name}':\n"
                                    f"{traceback.format_exc()}"
                                )
                                raise
                        else:
                            print(
                                f"[Violetear] ⚠️ Warning: Client {client_id} tried to call unknown realtime function '{func_name}'"
                            )

            except (WebSocketDisconnect, RuntimeError):
                await self.socket_manager.disconnect(client_id)
            except Exception:
                # A realtime handler raised (already logged above). Tear down
                # this connection and let the error propagate so it stays
                # visible instead of silently leaving the client hanging.
                await self.socket_manager.disconnect(client_id)
                raise

        # Client and Server registries
        self.client = ClientRegistry(self)
        self.server = ServerRegistry(self)

    def local[T](self, cls: type[T]) -> T:
        # Compile to JS at decoration time — fail fast on unsupported constructs
        js = transpile_class(cls)
        self.client._compiled_classes[cls.__name__] = js
        # Keep server-side reactive proxy (used for SSR initial values)
        return local(cls)

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

    def _generate_bundle_js(self) -> str:
        """Generate bundle.js: compiled state classes + functions + RPC stubs + hydrate call."""
        parts: list[str] = []

        # 1. Compiled state classes
        for js in self.client._compiled_classes.values():
            parts.append(js)

        # 2. Compiled client functions
        for fn_name, (kind, js) in self.client._compiled_functions.items():
            parts.append(js)

        # 3. JS RPC stubs for @app.server.rpc
        for name, func in self.server.rpc_functions.items():
            sig = inspect.signature(func)
            params = [p.name for p in sig.parameters.values() if p.name != "client_id"]
            param_str = ", ".join(params)
            destructured = ", ".join(params)
            parts.append(
                f"async function {name}({{{destructured}}}) {{\n"
                f'  const r = await fetch("/_violetear/rpc/{name}", {{\n'
                f'    method: "POST",\n'
                f'    headers: {{"Content-Type": "application/json"}},\n'
                f"    body: JSON.stringify({{{param_str}}})\n"
                f"  }});\n"
                f"  if (!r.ok) throw new Error(`RPC error: ${{r.status}}`);\n"
                f"  return r.json();\n"
                f"}}"
            )

        # 4. JS realtime stubs for @app.server.realtime
        for name, func in self.server.realtime_functions.items():
            sig = inspect.signature(func)
            params = [p.name for p in sig.parameters.values() if p.name != "client_id"]
            param_str = ", ".join(params)
            destructured = ", ".join(params)
            parts.append(
                f"async function {name}({{{destructured}}}) {{\n"
                f"  window.violetear_socket.send(JSON.stringify({{\n"
                f'    type: "realtime", func: "{name}",\n'
                f"    args: [], kwargs: {{{param_str}}}\n"
                f"  }}));\n"
                f"}}"
            )

        # 4.5 Validator registry for @app.client.realtime handlers.
        # Threaded into Violetear_hydrate so the WS dispatch can check inbound
        # kwargs before invoking the handler. Always emitted (possibly empty)
        # so runtime.js never references an undefined binding.
        validator_entries: list[str] = []
        for fn_name, (kind, _js) in self.client._compiled_functions.items():
            if kind == "realtime":
                spec = self.client._realtime_check_specs.get(fn_name, "{  }")
                validator_entries.append(f"  {fn_name}: {spec}")
        validators_block = ",\n".join(validator_entries)
        parts.append(f"const _VALIDATORS = {{\n{validators_block}\n}};")

        # 5. Scope object + hydrate call
        # Group by decorator kind for lifecycle dispatch
        lifecycle_entries: list[str] = []
        for event, fn_names in self.client._lifecycle.items():
            names_js = ", ".join(fn_names)
            lifecycle_entries.append(f"    {event}: [{names_js}]")

        # Non-lifecycle scope entries (callable by name from WS/DOM)
        scope_entries: list[str] = []
        for fn_name in self.client._compiled_functions:
            scope_entries.append(f"  {fn_name}")

        lifecycle_block = ",\n".join(lifecycle_entries)
        scope_block = ",\n".join(scope_entries)

        storage_prefix = self.storage_prefix or self.title.lower().replace(" ", "-")

        parts.append(
            f"const _scope = {{\n"
            f"  _lifecycle: {{\n{lifecycle_block}\n  }},\n"
            f"{scope_block}\n"
            f"}};\n"
            f'Violetear_hydrate(_scope, {{ storage_prefix: "{storage_prefix}", validators: _VALIDATORS }});'
        )

        return "\n\n".join(parts)

    def _version_url(self, url: str) -> str:
        """Appends the app version to the URL to bust caches."""
        delimiter = "&" if "?" in url else "?"
        return f"{url}{delimiter}v={self.version}"

    def _inject_client_side(self, doc: Document):
        """Inject the JS runtime and compiled bundle into the document."""
        if self.fade_in > 0:
            cloak_script = (
                'var cloak = document.createElement("style");'
                'cloak.id = "violetear-cloak";'
                'cloak.innerHTML = "body { opacity: 0; pointer-events: none; }";'
                "document.head.appendChild(cloak);"
            )
            doc.script(content=cloak_script)

        doc.script(src="/_violetear/runtime.js")
        bundle_url = self._version_url("/_violetear/bundle.js")
        doc.script(src=bundle_url, defer=True)

        if self.fade_in > 0:
            # Fade in after bundle loads — bundle.js calls Violetear_hydrate synchronously
            # so cloak removal can happen at end of bundle evaluation
            fade_ms = int(self.fade_in * 1000)
            fade_script = (
                f'document.addEventListener("DOMContentLoaded", () => {{'
                f'  const cloak = document.getElementById("violetear-cloak");'
                f"  if (cloak) {{"
                f'    cloak.innerHTML = "body {{ opacity: 1; pointer-events: auto; '
                f'transition: opacity {self.fade_in}s ease-in-out; }}";'
                f"    setTimeout(() => cloak.remove(), {fade_ms});"
                f"  }}"
                f"}});"
            )
            doc.script(content=fade_script)

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
            self._version_url("/_violetear/bundle.js"),
            self._version_url("/_violetear/runtime.js"),
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
        sw_script = (
            f"if ('serviceWorker' in navigator) {{\n"
            f"    window.addEventListener('load', () => {{\n"
            f"        navigator.serviceWorker.register('{sw_url}', {{ scope: '{path}' }})\n"
            f"            .then(reg => console.log('[Violetear] SW registered for {path}', reg))\n"
            f"            .catch(err => console.log('[Violetear] SW registration failed', err));\n"
            f"    }});\n"
            f"}}"
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

                    # Check if this document contains client bindings
                    if self.client._compiled_functions or self.client._compiled_classes:
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
