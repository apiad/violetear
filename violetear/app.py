import os
from typing import Any, Callable, Dict, Optional, List

# --- Optional Server Dependencies ---
try:
    from fastapi import FastAPI, APIRouter, Request
    from fastapi.responses import HTMLResponse, Response
    from fastapi.staticfiles import StaticFiles

    HAS_SERVER = True
except ImportError:
    HAS_SERVER = False
    # Dummy classes for type hinting if dependencies are missing
    # FastAPI = object  # type: ignore
    # APIRouter = object  # type: ignore
    # Request = object  # type: ignore


class App:
    """
    The main Violetear Application class.
    Wraps FastAPI to provide a full-stack Python web framework experience.
    """

    def __init__(self, title: str = "Violetear App"):
        if not HAS_SERVER:
            raise ImportError(
                "Violetear Server dependencies are missing. "
                "Please install them using `pip install violetear[server]`"
            )

        self.title = title
        self.api = FastAPI(title=title)
        self._routes: List[Dict[str, Any]] = []

        # We will add the Asset Registry here in Phase 2.2
        self.styles = {}

    def route(self, path: str, methods: List[str] = ["GET"]):
        """
        Decorator to register a route.
        Supports standard SSR (returning Documents) out of the box.
        """

        def decorator(func: Callable):
            # We will implement the wrapper logic in Phase 2.2
            self.api.add_api_route(path, func, methods=methods)
            return func

        return decorator

    def mount_static(self, directory: str, path: str = "/static"):
        """Mounts a static file directory."""
        if os.path.isdir(directory):
            self.api.mount(path, StaticFiles(directory=directory), name="static")

    def run(self, host="0.0.0.0", port=8000, **kwargs):
        """Helper to run via uvicorn programmatically."""
        import uvicorn

        uvicorn.run(self.api, host=host, port=port, **kwargs)
