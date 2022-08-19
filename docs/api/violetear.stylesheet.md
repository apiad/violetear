<a name="ref:StyleSheet"></a>

```python linenums="1"
import io
import datetime
from pathlib import Path
from warnings import warn
import textwrap
from .selector import Selector
from .style import Style
from .media import MediaQuery


class StyleSheet:
    def __init__(
        self, *styles: Style, normalize: bool = True, base: Style = None
    ) -> None:
        self.styles = list(styles)
        self.medias = []

        self._by_name = {}
        self._used = set()
        self._media = None
        self._base = base

        if normalize:
            self._preamble = open(Path(__file__).parent / "normalize.css").read()
        else:
            self._preamble = None

    def render(self, fp=None, *, dynamic: bool = False):
        opened = False

        if isinstance(fp, (str, Path)):
            fp = open(fp, "wt")
            opened = True

        if fp is None:
            fp = io.StringIO()
            opened = True

        self._write_preamble(fp, dynamic)

        for style in self.styles:
            self._render(style, fp, 0)

        for media in self.medias:
            fp.write(media.css())
            fp.write("{\n")

            for style in media.styles:
                self._render(style, fp, 4)

            fp.write("}\n\n")

        if isinstance(fp, io.StringIO):
            result = fp.getvalue()
        else:
            result = None

        if opened:
            fp.close()

        return result

    def _write_preamble(self, fp, dynamic):
        fp.write("/* Made with violetear */\n")

        if dynamic:
            fp.write(
                f"/* Generating {len(self._used)}/{len(self._by_name)} styles */\n"
            )
        else:
            fp.write(f"/* Generating all {len(self._by_name)} styles */\n")

        fp.write(f"/* Autogenerated on {datetime.datetime.now()} */\n\n")

        fp.write(self._preamble)

        if self._preamble:
            fp.write("\n")

    def _render(self, style: Style, fp, indent=0):
        for s in [style] + list(style._children):
            fp.write(textwrap.indent(s.css(), indent * " "))
            fp.write("\n\n")

    def select(self, selector: str, *, name: str = None):
        if name is None:
            name = (
                selector.replace("#", "_")
                .replace(".", "_")
                .replace("-", "_")
                .strip("_")
            )

        style = Style(Selector.from_css(selector))

        if self._base:
            style.apply(self._base)

        return self.add(style, name=name)

    def add(self, style: Style = None, *, name: str = None) -> Style:
        if self._media is None:
            self.styles.append(style)
        else:
            self._media.add(style)

        if name is not None:
            self._by_name[name] = style

        return style

    def media(self, min_width: int = None, max_width: int = None) -> MediaQuery:
        media = MediaQuery(self, min_width=min_width, max_width=max_width)
        self.medias.append(media)
        return media

    def redefine(self, style: Style) -> Style:
        style = Style(selector=style.selector)
        self.add(style=style)
        return style

    def __getitem__(self, key) -> Style:
        try:
            style = self._by_name[key]
            self._used.add(style)
            return style
        except KeyError:
            warn(f"Style {key} not defined")
            raise

    def __getattr__(self, key) -> Style:
        return self[key]
```
