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

    def __init__(self, cache_name: str = "violetear-v1"):
        self.cache_name = cache_name
        self.assets = set()

    def add_assets(self, *files: str):
        """Register files to be pre-cached during the 'install' phase."""
        self.assets.update(files)

    def render(self) -> str:
        """
        Generates the JavaScript code for the Service Worker.
        Implements a simple Cache-First strategy.
        """
        assets_json = json.dumps(list(sorted(self.assets)))

        return dedent(
            f"""
            const CACHE_NAME = "{self.cache_name}";
            const ASSETS = {assets_json};

            // 1. Install Phase: Cache all static assets
            self.addEventListener("install", (event) => {{
                event.waitUntil(
                    caches.open(CACHE_NAME).then((cache) => {{
                        console.log("[Service Worker] Caching all: app shell and content");
                        return cache.addAll(ASSETS);
                    }})
                );
            }});

            // 2. Activate Phase: Cleanup old caches (Optional but good practice)
            self.addEventListener("activate", (event) => {{
                event.waitUntil(
                    caches.keys().then((keyList) => {{
                        return Promise.all(keyList.map((key) => {{
                            if (key !== CACHE_NAME) {{
                                return caches.delete(key);
                            }}
                        }}));
                    }})
                );
            }});

            // 3. Fetch Phase: Cache First, Fallback to Network
            self.addEventListener("fetch", (event) => {{
                event.respondWith(
                    caches.match(event.request).then((response) => {{
                        return response || fetch(event.request);
                    }})
                );
            }});
            """
        )
