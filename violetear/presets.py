from violetear.stylesheet import StyleSheet


class FlexGrid(StyleSheet):
    def __init__(
        self, columns: int = 12, breakpoints=None, row_class="row", base_class="span"
    ) -> None:
        super().__init__()

        self._columns = columns
        self._row_class = row_class
        self._base_class = base_class

        self.select(f".{row_class}").flexbox(wrap=True)

        self._make_grid_styles(columns)

        if breakpoints is None:
            return

        for cls, (size, cols) in breakpoints.items():
            with self.media(max_width=size):
                self._make_grid_styles(cols, cls)

    def _make_grid_styles(self, columns, custom=None):
        for size in range(1, columns):
            self.select(f".span-{size}").width(size / columns)

        for size in range(columns, 13):
            self.select(f".span-{size}").width(1.0)

        if custom:
            for size in range(1, columns + 1):
                self.select(f".{custom}-{size}").width(size / columns)
