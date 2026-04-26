import math
from typing import Dict, Tuple, Optional, List, Set
from PyQt6.QtCore import Qt, QRectF
from pixeart.core.color import Color
from pixeart.core.selection_commands import MoveSelectionCommand, PasteCommand, DeleteSelectionCommand
from .base_tool import BaseTool


class SelectionTool(BaseTool):
    """
    Profesyonel Seçim Aracı:
    - Dikdörtgen seçim (Rectangle Marquee)
    - Serbest çizgi seçimi (Lasso)
    - Seçimi taşıma (Move)
    - Seçimi kopyalama (Copy + Paste)
    - Seçimi silme (Delete)

    Modlar:
    - "rect": Dikdörtgen seçim
    - "lasso": Serbest çizgi seçimi
    """
    def __init__(self):
        super().__init__()
        self.mode = "rect"
        self._start_x = 0
        self._start_y = 0
        self._is_selecting = False
        self._is_moving = False
        self._move_start_x = 0
        self._move_start_y = 0

        self.selection_pixels: Set[Tuple[int, int]] = set()
        self.clipboard: Dict[Tuple[int, int], Optional[Color]] = {}

        self._lasso_points: List[Tuple[int, int]] = []

    def on_press(self, x: int, y: int, button: Qt.MouseButton) -> None:
        if not self.manager or not self.manager.document:
            return
        if button != Qt.MouseButton.LeftButton:
            return

        # Eğer mevcut bir seçim varsa ve tıklanan nokta seçim içindeyse, taşıma başlat
        if self.selection_pixels and (x, y) in self.selection_pixels:
            self._is_moving = True
            self._move_start_x = x
            self._move_start_y = y
            return

        # Yeni seçim başlat
        self._clear_scene_selection()
        self.selection_pixels.clear()
        self._start_x = x
        self._start_y = y
        self._is_selecting = True

        if self.mode == "lasso":
            self._lasso_points = [(x, y)]

    def on_drag(self, x: int, y: int, button: Qt.MouseButton) -> None:
        if not self.manager or not self.manager.document:
            return

        if self._is_moving:
            return

        if self._is_selecting:
            if self.mode == "rect":
                self._update_rect_selection(x, y)
            elif self.mode == "lasso":
                self._lasso_points.append((x, y))
                self._update_lasso_preview()

    def on_release(self, x: int, y: int, button: Qt.MouseButton) -> None:
        if not self.manager or not self.manager.document:
            return

        if self._is_moving:
            dx = x - self._move_start_x
            dy = y - self._move_start_y
            if dx != 0 or dy != 0:
                self._execute_move(dx, dy)
            self._is_moving = False
            return

        if self._is_selecting:
            self._is_selecting = False
            if self.mode == "rect":
                self._finalize_rect_selection(x, y)
            elif self.mode == "lasso":
                self._finalize_lasso_selection()

    # --- Dikdörtgen Seçim ---
    def _update_rect_selection(self, x: int, y: int):
        x1 = min(self._start_x, x)
        y1 = min(self._start_y, y)
        x2 = max(self._start_x, x)
        y2 = max(self._start_y, y)
        if self.manager.canvas_scene:
            self.manager.canvas_scene.set_selection_rect(QRectF(x1, y1, x2 - x1 + 1, y2 - y1 + 1))

    def _finalize_rect_selection(self, x: int, y: int):
        doc = self.manager.document
        x1 = max(0, min(self._start_x, x))
        y1 = max(0, min(self._start_y, y))
        x2 = min(doc.width - 1, max(self._start_x, x))
        y2 = min(doc.height - 1, max(self._start_y, y))

        for py in range(y1, y2 + 1):
            for px in range(x1, x2 + 1):
                self.selection_pixels.add((px, py))

        if self.manager.canvas_scene:
            self.manager.canvas_scene.set_selection_rect(QRectF(x1, y1, x2 - x1 + 1, y2 - y1 + 1))

    # --- Lasso Seçimi ---
    def _update_lasso_preview(self):
        if len(self._lasso_points) < 2:
            return
        xs = [p[0] for p in self._lasso_points]
        ys = [p[1] for p in self._lasso_points]
        if self.manager.canvas_scene:
            self.manager.canvas_scene.set_selection_rect(
                QRectF(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
            )

    def _finalize_lasso_selection(self):
        if len(self._lasso_points) < 3:
            self._lasso_points.clear()
            return

        doc = self.manager.document
        self.selection_pixels = self._rasterize_polygon(self._lasso_points, doc.width, doc.height)

        if self.selection_pixels:
            xs = [p[0] for p in self.selection_pixels]
            ys = [p[1] for p in self.selection_pixels]
            if self.manager.canvas_scene:
                self.manager.canvas_scene.set_selection_rect(
                    QRectF(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
                )

        self._lasso_points.clear()

    @staticmethod
    def _rasterize_polygon(points: List[Tuple[int, int]], max_w: int, max_h: int) -> Set[Tuple[int, int]]:
        if not points:
            return set()

        ys_all = [p[1] for p in points]
        min_y = max(0, min(ys_all))
        max_y = min(max_h - 1, max(ys_all))

        filled = set()
        n = len(points)

        for y in range(min_y, max_y + 1):
            intersections = []
            for i in range(n):
                j = (i + 1) % n
                y1, y2 = points[i][1], points[j][1]
                x1, x2 = points[i][0], points[j][0]

                if y1 == y2:
                    continue
                if y < min(y1, y2) or y >= max(y1, y2):
                    continue

                x_inter = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                intersections.append(x_inter)

            intersections.sort()
            for k in range(0, len(intersections) - 1, 2):
                x_start = max(0, int(math.ceil(intersections[k])))
                x_end = min(max_w - 1, int(math.floor(intersections[k + 1])))
                for x in range(x_start, x_end + 1):
                    filled.add((x, y))

        return filled

    # --- Taşıma ---
    def _execute_move(self, dx: int, dy: int):
        doc = self.manager.document
        layer_idx = doc.active_layer_index
        if layer_idx < 0 or layer_idx >= len(doc.layers):
            return

        layer = doc.layers[layer_idx]
        pixels_to_move = {}
        for (px, py) in self.selection_pixels:
            if doc.in_bounds(px, py):
                c = layer.get_pixel(px, py)
                pixels_to_move[(px, py)] = c if not c.is_transparent else None

        if not pixels_to_move:
            return

        cmd = MoveSelectionCommand(doc, layer_idx, pixels_to_move, dx, dy)
        self.manager.commit_command(cmd)

        # Seçim alanını da taşı
        new_sel = set()
        for (px, py) in self.selection_pixels:
            new_sel.add((px + dx, py + dy))
        self.selection_pixels = new_sel

        if self.manager.canvas_scene and self.selection_pixels:
            xs = [p[0] for p in self.selection_pixels]
            ys = [p[1] for p in self.selection_pixels]
            self.manager.canvas_scene.set_selection_rect(
                QRectF(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
            )

    # --- Kopyalama ---
    def copy_selection(self):
        if not self.manager or not self.manager.document or not self.selection_pixels:
            return

        doc = self.manager.document
        layer_idx = doc.active_layer_index
        if layer_idx < 0:
            return

        layer = doc.layers[layer_idx]
        self.clipboard.clear()

        xs = [p[0] for p in self.selection_pixels]
        ys = [p[1] for p in self.selection_pixels]
        ox, oy = min(xs), min(ys)

        for (px, py) in self.selection_pixels:
            if doc.in_bounds(px, py):
                c = layer.get_pixel(px, py)
                if not c.is_transparent:
                    self.clipboard[(px - ox, py - oy)] = c

    def paste_clipboard(self, offset_x: int = 0, offset_y: int = 0):
        if not self.manager or not self.manager.document or not self.clipboard:
            return

        doc = self.manager.document
        layer_idx = doc.active_layer_index
        if layer_idx < 0:
            return

        cmd = PasteCommand(doc, layer_idx, dict(self.clipboard), offset_x, offset_y)
        self.manager.commit_command(cmd)

    def delete_selection(self):
        if not self.manager or not self.manager.document or not self.selection_pixels:
            return

        doc = self.manager.document
        layer_idx = doc.active_layer_index
        if layer_idx < 0:
            return

        layer = doc.layers[layer_idx]
        pixels = {}
        for (px, py) in self.selection_pixels:
            if doc.in_bounds(px, py):
                c = layer.get_pixel(px, py)
                pixels[(px, py)] = c if not c.is_transparent else None

        if pixels:
            cmd = DeleteSelectionCommand(doc, layer_idx, pixels)
            self.manager.commit_command(cmd)

    def clear_selection(self):
        self.selection_pixels.clear()
        self._clear_scene_selection()

    def _clear_scene_selection(self):
        if self.manager and self.manager.canvas_scene:
            self.manager.canvas_scene.set_selection_rect(None)

    def transform_selection(self, transform_type: str, bbox: Tuple[int, int, int, int]):
        if not self.selection_pixels: return
        
        # We need a proxy dict to use get_rotated etc.
        dummy_pixels = {p: None for p in self.selection_pixels}
        doc = self.manager.document
        
        if transform_type == "flip_h":
            res = doc.get_flipped_horizontal(dummy_pixels, bbox)
        elif transform_type == "flip_v":
            res = doc.get_flipped_vertical(dummy_pixels, bbox)
        elif transform_type == "rot_180":
            res = doc.get_rotated(dummy_pixels, 180, bbox)
        elif transform_type == "rot_90cw":
            res = doc.get_rotated(dummy_pixels, 90, bbox)
        elif transform_type == "rot_90ccw":
            res = doc.get_rotated(dummy_pixels, 270, bbox)
        else:
            return
            
        self.selection_pixels = set(res.keys())
        
        if self.manager.canvas_scene and self.selection_pixels:
            xs = [p[0] for p in self.selection_pixels]
            ys = [p[1] for p in self.selection_pixels]
            self.manager.canvas_scene.set_selection_rect(
                QRectF(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
            )
