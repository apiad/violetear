class Selector:
    def __init__(self, id: str = None, *class_name: str) -> None:
        self._id = id
        self._class_name = class_name

    def css(self) -> str:
        parts = []

        if self._id:
            parts.append(f"#{self._id}")

        for cls in self._class_name:
            parts.append(f".{cls}")

        return "".join(parts)
