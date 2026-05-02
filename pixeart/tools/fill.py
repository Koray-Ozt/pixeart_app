from collections import deque
from PyQt6.QtCore import Qt
from pixeart.core.color import Color
from pixeart.core.commands import DrawCommand
from .base_tool import BaseTool

class FillTool(BaseTool):
    def on_press(self, x: int, y: int, button: Qt.MouseButton) -> None:
        if not self.manager or not self.manager.document:
            return

        doc = self.manager.document
        layer_idx = doc.active_layer_index
        
        if layer_idx < 0 or layer_idx >= len(doc.layers):
            return

        layer = doc.layers[layer_idx]
        if not layer.is_visible or layer.is_locked:
            return

        if not doc.in_bounds(x, y):
            return

        target_color = layer.get_pixel(x, y)
        fill_color = self.manager.get_active_color(button)

        # If both transparent, nothing to do. If no selection, and the
        # clicked pixel already equals the fill color, skip (no-op).
        if (target_color.is_transparent and fill_color.is_transparent):
            return

        sel_tool = self.manager.tools.get("selection") if hasattr(self.manager, 'tools') else None
        selection_checker = sel_tool.is_point_selected if sel_tool and getattr(sel_tool, 'selection_pixels', None) else None
        if selection_checker is None and (target_color == fill_color):
            return

        # If a selection exists, fill the entire selection mask regardless of
        # internal color connectivity — the user expects the whole selected
        # region to be filled. If no selection, fall back to classic flood-fill
        # behavior that respects contiguous color regions.
        sel_tool = self.manager.tools.get("selection") if hasattr(self.manager, 'tools') else None
        selection_pixels = sel_tool.selection_pixels if sel_tool and getattr(sel_tool, 'selection_pixels', None) else None

        before_pixels = {}
        after_pixels = {}

        if selection_pixels is not None:
            # Fill every pixel in the selection mask
            for (px, py) in list(selection_pixels):
                if not doc.in_bounds(px, py):
                    continue
                current_color = layer.get_pixel(px, py)
                if (px, py) not in before_pixels:
                    before_pixels[(px, py)] = current_color if not current_color.is_transparent else None
                # Even if the color is already equal, we record and set to ensure
                # selection is uniformly filled
                after_pixels[(px, py)] = fill_color
                if fill_color is None:
                    layer.set_pixel(px, py, Color(0, 0, 0, 0))
                else:
                    layer.set_pixel(px, py, fill_color)
                self.manager.update_canvas_pixel(px, py, fill_color)
        else:
            # No selection: behave like a regular flood fill constrained by color
            queue = deque([(x, y)])
            visited = set([(x, y)])

            while queue:
                cx, cy = queue.popleft()

                current_color = layer.get_pixel(cx, cy)

                before_pixels[(cx, cy)] = current_color if not current_color.is_transparent else None
                after_pixels[(cx, cy)] = fill_color

                layer.set_pixel(cx, cy, fill_color)
                self.manager.update_canvas_pixel(cx, cy, fill_color)

                for nx, ny in ((cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)):
                    if (nx, ny) not in visited and doc.in_bounds(nx, ny):
                        neighbor_color = layer.get_pixel(nx, ny)
                        is_match = (neighbor_color.is_transparent and target_color.is_transparent) or (neighbor_color == target_color)
                        if is_match:
                            visited.add((nx, ny))
                            queue.append((nx, ny))

        if after_pixels:
            command = DrawCommand(
                document=doc,
                frame_index=doc.active_frame_index,
                layer_index=layer_idx,
                before_pixels=before_pixels,
                after_pixels=after_pixels
            )
            self.manager.commit_command(command)

    def on_drag(self, x: int, y: int, button: Qt.MouseButton) -> None:
        pass

    def on_release(self, x: int, y: int, button: Qt.MouseButton) -> None:
        pass
