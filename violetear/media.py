from .style import Style


class MediaQuery:
    def __init__(self, sheet, min_width: int = None, max_width: int = None) -> None:
        super().__init__()

        self._sheet = sheet

        self.min_width = min_width
        self.max_width = max_width
        self.styles = []

    def add(self, style: Style):
        self.styles.append(style)

    def css(self) -> str:
        query = []

        if self.min_width:
            query.append(f"(min-width: {self.min_width}px)")

        if self.max_width:
            query.append(f"(max-width: {self.max_width}px)")

        return f"\n@media {' and '.join(query)}"

    def clone(self, sheet) -> "MediaQuery":
        media = MediaQuery(sheet, self.min_width, self.max_width)

        for style in self.styles:
            media.add(style)

        return media

    def __enter__(self):
        self._sheet._media = self

    def __exit__(self, *args, **kwargs):
        self._sheet._media = None
