import json
from dataclasses import dataclass, asdict, field
from textwrap import dedent
from typing import List, Optional


@dataclass
class Icon:
    """
    Represents an icon in the Web App Manifest.
    """

    src: str
    sizes: str
    type: str = "image/png"
    purpose: str = "any maskable"


@dataclass
class Manifest:
    """
    Represents a Web App Manifest file (manifest.json).
    Controls how the app appears when installed on a device.
    """

    name: str
    short_name: Optional[str] = None
    start_url: str = "."
    display: str = "standalone"
    background_color: str = "#ffffff"
    theme_color: str = "#ffffff"
    description: str = ""
    icons: List[Icon] = field(default_factory=list)
    scope: str = "/"

    def add_icon(
        self,
        src: str,
        sizes: str,
        type: str = "image/png",
        purpose: str = "any maskable",
    ):
        """Fluent helper to add an icon."""
        self.icons.append(Icon(src, sizes, type, purpose))
        return self

    def render(self) -> str:
        """Serializes the manifest to a JSON string."""
        data = asdict(self)
        # Remove keys with None values to keep the JSON clean
        data = {k: v for k, v in data.items() if v is not None}
        return json.dumps(data, indent=2)


class ServiceWorker:
    """
    Generates the Service Worker script (sw.js).
    Handles asset caching for offline support.
    """

    def __init__(self, version: str, cache_name: str = "violetear-{}"):
        self.version = version
        self.cache_name = cache_name.format(version)
        self.assets = set()

    def add_assets(self, *files: str | None):
        """Register files to be pre-cached during the 'install' phase."""
        self.assets.update([f for f in files if f])

    def render(self) -> str:
        """
        Generates the JavaScript code for the Service Worker.
        Implements a Network-First strategy for navigation and Cache-First for assets.
        """
        assets_json = json.dumps(list(sorted(self.assets)))

        return dedent(
            f"""
            const CACHE_NAME = "{self.cache_name}";
            const ASSETS = {assets_json};

            // 1. Install Phase: Cache all static assets
            self.addEventListener("install", (event) => {{
                // Force the waiting service worker to become the active service worker
                self.skipWaiting();

                event.waitUntil(
                    caches.open(CACHE_NAME).then((cache) => {{
                        console.log("[Service Worker] Caching all: app shell and content");
                        return cache.addAll(ASSETS);
                    }})
                );
            }});

            // 2. Activate Phase: Cleanup old caches
            self.addEventListener("activate", (event) => {{
                event.waitUntil(
                    caches.keys().then((keyList) => {{
                        return Promise.all(keyList.map((key) => {{
                            if (key !== CACHE_NAME) {{
                                console.log("[SW] Removing old cache:", key);
                                return caches.delete(key);
                            }}
                        }}));
                    }}).then(() => {{
                        // Tell the active service worker to take control of the page immediately
                        return self.clients.claim();
                    }})
                );
            }});

            // 3. Fetch Phase
            self.addEventListener("fetch", (event) => {{
                // Navigation requests (HTML): Network First, fall back to Cache
                // This ensures users always get the latest Python/HTML logic if online.
                if (event.request.mode === 'navigate') {{
                    event.respondWith(
                        fetch(event.request).catch(() => {{
                            return caches.match(event.request);
                        }})
                    );
                    return;
                }}

                // Assets (CSS, JS, Images, Pyodide): Cache First, fall back to Network
                // These should be versioned by the app (e.g. ?v=...) so we can trust the cache.
                event.respondWith(
                    caches.match(event.request).then((response) => {{
                        return response || fetch(event.request);
                    }})
                );
            }});
            """
        )
