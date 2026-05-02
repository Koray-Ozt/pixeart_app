from PyQt6.QtCore import Qt
from pixeart.core.color import Color
from .pencil import PencilTool

class EraserTool(PencilTool):
    """
    Silgi Aracı (Eraser Tool)
    PencilTool'dan miras alır, tek farkı rengin her zaman None (saydam) olmasıdır.
    Simetri desteği PencilTool._apply_brush() aracılığıyla otomatik miras alınır.
    """

    def _get_draw_color(self, button: Qt.MouseButton):
        return None

    def _apply_brush(self, cx: int, cy: int, button: Qt.MouseButton) -> None:
        doc = self.manager.document
        layer_idx = doc.active_layer_index
        if layer_idx < 0 or layer_idx >= len(doc.layers):
            return

        layer = doc.layers[layer_idx]
        if not layer.is_visible or layer.is_locked:
            return

        size = self.manager.brush_size
        shape = self.manager.brush_shape

        sym_points = self.manager.get_symmetry_points(cx, cy)

        for sx, sy in sym_points:
            pixels = self._get_brush_pixels(sx, sy, size, shape)

            for px, py in pixels:
                if not doc.in_bounds(px, py):
                    continue

                # Respect selection mask if present (use robust check)
                sel_tool = self.manager.tools.get("selection") if hasattr(self.manager, 'tools') else None
                if sel_tool and getattr(sel_tool, 'selection_pixels', None):
                    if not sel_tool.is_point_selected(px, py):
                        continue

                current_color = layer.get_pixel(px, py)

                if (px, py) not in self.before_pixels:
                    self.before_pixels[(px, py)] = current_color if not current_color.is_transparent else None

                if current_color.is_transparent:
                    continue

                self.after_pixels[(px, py)] = None

                layer.set_pixel(px, py, Color(0, 0, 0, 0))
                self.manager.update_canvas_pixel(px, py, None)
