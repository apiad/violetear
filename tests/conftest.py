"""
Shared test fixtures for violetear.

Most of the suite runs against `TestClient` (sync, in-process). The e2e tests
(marked `@pytest.mark.e2e`) need a real port-bound server because Playwright
drives a real Chromium that fetches HTTP/WS resources from a URL.
"""

import importlib.util
import os
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Callable

import httpx
import pytest
import uvicorn

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"


# ---- Playwright browser-launch override ------------------------------------
# pytest-playwright defaults to the `chromium_headless_shell-<rev>` binary for
# headless mode. On systems where that variant isn't installed (e.g. the full
# `chromium-<rev>` was installed but the headless-shell wasn't), we fall back
# to launching the full chromium binary in headless mode. This avoids the
# common "Executable doesn't exist at .../chrome-headless-shell" error when
# CI or dev has only one of the two variants on disk.


def _find_full_chromium() -> str | None:
    """Locate a usable full chromium binary under PLAYWRIGHT_BROWSERS_PATH."""
    root = Path(
        os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
        or (Path.home() / ".cache" / "ms-playwright")
    )
    if not root.exists():
        return None
    # Pick the newest chromium-<rev>/chrome-linux64/chrome on disk.
    candidates = sorted(root.glob("chromium-*/chrome-linux64/chrome"), reverse=True)
    return str(candidates[0]) if candidates else None


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Override pytest-playwright's launch args to use the full chromium
    binary instead of the headless_shell variant.

    pytest-playwright defaults to a `chromium_headless_shell-<rev>` binary
    that often isn't installed (the standard `playwright install chromium`
    sometimes only fetches the full chromium). Pointing executable_path at
    the full chromium with headless launch produces equivalent behavior
    without the version-mismatch error.

    Set VIOLETEAR_PLAYWRIGHT_USE_HEADLESS_SHELL=1 to opt out of the override.
    """
    args = dict(browser_type_launch_args)
    if os.environ.get("VIOLETEAR_PLAYWRIGHT_USE_HEADLESS_SHELL"):
        return args
    chromium = _find_full_chromium()
    if chromium:
        args["executable_path"] = chromium
    return args


def _free_port() -> int:
    """Bind to port 0, get the OS-assigned port, release. Standard race-tolerant
    pattern — there's a tiny window between release and uvicorn binding but
    uvicorn errors loudly if it can't bind."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _load_example(filename: str):
    """Import an example module by filename, registering in sys.modules first
    so violetear's bundle generator can call inspect.getsource on its state
    classes (see issues/7.5)."""
    name = filename.removesuffix(".py").replace(".", "_")
    spec = importlib.util.spec_from_file_location(name, EXAMPLES_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def example_server() -> Callable[[str], str]:
    """Boot one of the canonical examples on a free port via uvicorn-in-thread,
    yield a factory that returns the base URL. The server tears down at end of
    test."""
    servers: list[tuple[uvicorn.Server, threading.Thread]] = []

    def _start(filename: str) -> str:
        port = _free_port()
        module = _load_example(filename)

        config = uvicorn.Config(
            module.app.api,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            lifespan="on",
        )
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        servers.append((server, thread))

        # Wait for the server to actually accept connections.
        base = f"http://127.0.0.1:{port}"
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            try:
                httpx.get(base + "/", timeout=0.4)
                return base
            except httpx.HTTPError:
                time.sleep(0.05)
        raise RuntimeError(f"Example server {filename} did not start within 10s")

    yield _start

    # Teardown — request graceful exit, give it a moment, then drop the threads.
    for server, _thread in servers:
        server.should_exit = True
    for _server, thread in servers:
        thread.join(timeout=3.0)
