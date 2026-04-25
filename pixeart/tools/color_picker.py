from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from .base_tool import BaseTool
from pixeart.core.color import Color

class ColorPickerTool(BaseTool):
    def on_press(self, x: int, y: int, button: Qt.MouseButton) -> None:
        self._pick_color(x, y, button)

    def on_drag(self, x: int, y: int, button: Qt.MouseButton) -> None:
        self._pick_color(x, y, button)

    def on_release(self, x: int, y: int, button: Qt.MouseButton) -> None:
        pass

    def _pick_color(self, x: int, y: int, button: Qt.MouseButton) -> None:
        if not self.manager or not self.manager.document:
            return

        doc = self.manager.document
        if not doc.in_bounds(x, y):
            return

        picked_color: Optional[Color] = None

        # Yukarıdan aşağıya görünür katmanlarda rengi ara
        for layer in reversed(doc.layers):
            if not layer.is_visible:
                continue
            
            color = layer.get_pixel(x, y)
            if not color.is_transparent:
                picked_color = color
                break

        if picked_color is None:
            return

        qt_color = QColor(*picked_color.to_rgba_tuple())
        self.manager.notify_color_picked(qt_color, button)
