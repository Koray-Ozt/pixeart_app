import math
import logging
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
        self._start_x = 0.0
        self._start_y = 0.0
        self._is_selecting = False
        self._is_moving = False
        self._move_start_x = 0.0
        self._move_start_y = 0.0

        self.selection_pixels: Set[Tuple[int, int]] = set()
        self.clipboard: Dict[Tuple[int, int], Optional[Color]] = {}

        self._lasso_points: List[Tuple[float, float]] = []
        # Track selection shape/type so moves preserve the visual form
        self._selection_type: Optional[str] = None  # 'rect'|'lasso'|'circle'
        self._last_lasso_points: Optional[List[Tuple[int, int]]] = None
        self._last_circle_center: Optional[Tuple[float, float]] = None
        self._last_circle_radius: Optional[float] = None
        self._last_rect: Optional[Tuple[int, int, int, int]] = None
        # Debugging flag for move issues
        self._debug_move = True
        # Move snapshots used to keep preview and final move consistent
        self._move_orig_selection_pixels: Optional[Set[Tuple[int, int]]] = None
        self._move_orig_last_lasso_points: Optional[List[Tuple[int, int]]] = None
        self._move_orig_circle_center: Optional[Tuple[float, float]] = None
        self._move_orig_circle_radius: Optional[float] = None

    def on_press(self, x: float, y: float, button: Qt.MouseButton) -> None:
        if not self.manager or not self.manager.document:
            return
        # Right-click clears the selection
        if button == Qt.MouseButton.RightButton:
            self.clear_selection()
            return
        if button != Qt.MouseButton.LeftButton:
            return

        # Eğer mevcut bir seçim varsa ve tıklanan nokta seçim içindeyse, taşıma başlat
        # Use integer pixel coords for membership checks, but keep float
        # start positions so previews follow the cursor precisely.
        ix, iy = int(x), int(y)
        if self.selection_pixels and (ix, iy) in self.selection_pixels:
            self._is_moving = True
            self._move_start_x = float(x)
            self._move_start_y = float(y)
            # Snapshot geometry so preview and final move use the same base
            self._move_orig_selection_pixels = set(self.selection_pixels)
            self._move_orig_last_lasso_points = list(self._last_lasso_points) if self._last_lasso_points else None
            self._move_orig_circle_center = tuple(self._last_circle_center) if self._last_circle_center is not None else None
            self._move_orig_circle_radius = float(self._last_circle_radius) if self._last_circle_radius is not None else None
            if self._debug_move:
                try:
                    xs = [p[0] for p in self.selection_pixels]
                    ys = [p[1] for p in self.selection_pixels]
                    bbox = (min(xs), min(ys), max(xs), max(ys)) if xs and ys else None
                except Exception:
                    bbox = None
                print(f"[selection-debug] move_start at {(x,y)} sel_count={len(self.selection_pixels)} bbox={bbox}")
            return

        # Yeni seçim başlat
        self._clear_scene_selection()
        self.selection_pixels.clear()
        self._start_x = float(x)
        self._start_y = float(y)
        self._is_selecting = True
        if self.mode == "lasso":
            self._lasso_points = [(float(x), float(y))]
        elif self.mode == "circle":
            # For circle mode, store center (float)
            self._lasso_points = []
            self._circle_center = (float(x), float(y))

    def on_drag(self, x: float, y: float, button: Qt.MouseButton) -> None:
        if not self.manager or not self.manager.document:
            return

        if self._is_moving:
            dx = float(x) - float(self._move_start_x)
            dy = float(y) - float(self._move_start_y)
            # also compute integer pixel translation used at commit time
            dx_int = int(round(dx))
            dy_int = int(round(dy))
            if not self.manager.canvas_scene:
                return
            # Use the snapshot geometry if present so preview matches final move
            base_lasso = self._move_orig_last_lasso_points if self._move_orig_last_lasso_points is not None else self._last_lasso_points
            base_circle_center = self._move_orig_circle_center if self._move_orig_circle_center is not None else self._last_circle_center
            base_circle_radius = self._move_orig_circle_radius if self._move_orig_circle_radius is not None else self._last_circle_radius
            base_pixels = self._move_orig_selection_pixels if self._move_orig_selection_pixels is not None else self.selection_pixels

            if self._debug_move:
                try:
                    if base_pixels:
                        xs = [p[0] for p in base_pixels]
                        ys = [p[1] for p in base_pixels]
                        base_bbox = (min(xs), min(ys), max(xs), max(ys))
                        preview_bbox = (base_bbox[0] + dx, base_bbox[1] + dy, base_bbox[2] + dx, base_bbox[3] + dy)
                    else:
                        base_bbox = None
                        preview_bbox = None
                except Exception:
                    base_bbox = None
                    preview_bbox = None
                print(f"[selection-debug] preview dx={dx} dy={dy} base_bbox={base_bbox} preview_bbox={preview_bbox}")

            # Live preview while moving selection; do not commit until release
            if self._selection_type == 'lasso' and base_lasso:
                # Use polygon outline preview (shifted lasso points) for smooth,
                # cursor-anchored preview. Clear any pixel-mask preview to avoid
                # visual mismatch.
                # preview should use integer translation to match committed move
                shifted = [(px + dx_int, py + dy_int) for px, py in base_lasso]
                try:
                    if hasattr(self.manager.canvas_scene, 'set_preview_selection_mask'):
                        self.manager.canvas_scene.set_preview_selection_mask(None)
                except Exception:
                    pass
                if hasattr(self.manager.canvas_scene, 'set_selection_polygon'):
                    self.manager.canvas_scene.set_selection_polygon(shifted)
                else:
                    xs = [p[0] for p in shifted]
                    ys = [p[1] for p in shifted]
                    self.manager.canvas_scene.set_selection_rect(QRectF(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))
            elif self._selection_type == 'circle' and base_circle_center is not None and base_circle_radius is not None:
                cx, cy = base_circle_center
                ncx, ncy = cx + dx, cy + dy
                # Show outline preview of the circle by shifting the approximating
                # polygon. Clear any pixel-mask preview first.
                try:
                    if hasattr(self.manager.canvas_scene, 'set_preview_selection_mask'):
                        self.manager.canvas_scene.set_preview_selection_mask(None)
                except Exception:
                    pass
                if hasattr(self.manager.canvas_scene, 'set_selection_polygon'):
                    pts = []
                    r = base_circle_radius
                    steps = max(16, min(96, int(2 * math.pi * max(1.0, r))))
                    for i in range(steps):
                        theta = 2 * math.pi * i / steps
                        fx = ncx + r * math.cos(theta)
                        fy = ncy + r * math.sin(theta)
                        pts.append((fx, fy))
                    # shift polygon by integer translation for preview
                    pts_shifted = [(px + dx_int, py + dy_int) for px, py in pts]
                    self.manager.canvas_scene.set_selection_polygon(pts_shifted)
                else:
                    if base_pixels:
                        xs = [p[0] for p in base_pixels]
                        ys = [p[1] for p in base_pixels]
                        self.manager.canvas_scene.set_selection_rect(QRectF(min(xs) + dx_int, min(ys) + dy_int, max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))
            else:
                # Always use base_pixels bbox (current snapshot) so stale
                # _last_rect does not cause offset on repeated moves.
                if base_pixels:
                    xs = [p[0] for p in base_pixels]
                    ys = [p[1] for p in base_pixels]
                    self.manager.canvas_scene.set_selection_rect(QRectF(min(xs) + dx_int, min(ys) + dy_int, max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))
                elif self._last_rect:
                    x1, y1, x2, y2 = self._last_rect
                    self.manager.canvas_scene.set_selection_rect(QRectF(x1 + dx_int, y1 + dy_int, x2 - x1 + 1, y2 - y1 + 1))
            return

        if self._is_selecting:
            if self.mode == "rect":
                self._update_rect_selection(x, y)
            elif self.mode == "lasso":
                # Append points for lasso preview
                self._lasso_points.append((float(x), float(y)))
                self._update_lasso_preview()
            elif self.mode == "circle":
                # Update circle preview using stored center
                cx, cy = getattr(self, '_circle_center', (self._start_x, self._start_y))
                r = float(math.hypot(float(x) - cx, float(y) - cy))
                # approximate circle as polygon for preview
                if self.manager.canvas_scene and hasattr(self.manager.canvas_scene, 'set_selection_polygon'):
                    pts = []
                    steps = max(16, min(48, int(2 * math.pi * max(1.0, r))))
                    for i in range(steps):
                        theta = 2 * math.pi * i / steps
                        fx = cx + r * math.cos(theta)
                        fy = cy + r * math.sin(theta)
                        pts.append((fx, fy))
                    self.manager.canvas_scene.set_selection_polygon(pts)
                else:
                    x1 = max(0, cx - r)
                    y1 = max(0, cy - r)
                    x2 = min(self.manager.document.width - 1, cx + r)
                    y2 = min(self.manager.document.height - 1, cy + r)
                    if self.manager.canvas_scene:
                        self.manager.canvas_scene.set_selection_rect(
                            QRectF(x1, y1, x2 - x1 + 1, y2 - y1 + 1)
                        )

    def on_release(self, x: float, y: float, button: Qt.MouseButton) -> None:
        if not self.manager or not self.manager.document:
            return

        if self._is_moving:
            dx = float(x) - float(self._move_start_x)
            dy = float(y) - float(self._move_start_y)
            if self._debug_move:
                print(f"[selection-debug] release at {(x,y)} move_start={(self._move_start_x,self._move_start_y)} dx={dx} dy={dy}")
            if dx != 0 or dy != 0:
                # Commit integer pixel move (round to nearest pixel)
                self._execute_move(int(round(dx)), int(round(dy)))
            self._is_moving = False
            return

        if self._is_selecting:
            self._is_selecting = False
            if self.mode == "rect":
                self._finalize_rect_selection(x, y)
            elif self.mode == "lasso":
                self._finalize_lasso_selection()
            elif self.mode == "circle":
                self._finalize_circle_selection(x, y)

    # --- Dikdörtgen Seçim ---
    def _update_rect_selection(self, x: int, y: int):
        x1 = min(self._start_x, float(x))
        y1 = min(self._start_y, float(y))
        x2 = max(self._start_x, float(x))
        y2 = max(self._start_y, float(y))
        if self.manager.canvas_scene:
            self.manager.canvas_scene.set_selection_rect(QRectF(x1, y1, x2 - x1 + 1, y2 - y1 + 1))

    def _finalize_rect_selection(self, x: float, y: float):
        doc = self.manager.document
        # Convert float bounds to integer pixel inclusions
        x_min = max(0, int(math.floor(min(self._start_x, float(x)))))
        y_min = max(0, int(math.floor(min(self._start_y, float(y)))))
        x_max = min(doc.width - 1, int(math.ceil(max(self._start_x, float(x)))))
        y_max = min(doc.height - 1, int(math.ceil(max(self._start_y, float(y)))))

        for py in range(y_min, y_max + 1):
            for px in range(x_min, x_max + 1):
                self.selection_pixels.add((px, py))

        # Compute display rect and remember rectangle selection (ints)
        x1 = x_min
        y1 = y_min
        x2 = x_max
        y2 = y_max

        if self.manager.canvas_scene:
            self.manager.canvas_scene.set_selection_rect(QRectF(x1, y1, x2 - x1 + 1, y2 - y1 + 1))
        # remember rectangle selection
        self._selection_type = 'rect'
        self._last_rect = (x1, y1, x2, y2)

    # --- Lasso Seçimi ---
    def _update_lasso_preview(self):
        if len(self._lasso_points) < 2:
            return
        xs = [p[0] for p in self._lasso_points]
        ys = [p[1] for p in self._lasso_points]
        if self.manager.canvas_scene:
            # Use polygon preview if supported
            if hasattr(self.manager.canvas_scene, 'set_selection_polygon'):
                self.manager.canvas_scene.set_selection_polygon(self._lasso_points)
            else:
                self.manager.canvas_scene.set_selection_rect(
                    QRectF(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
                )

    def _finalize_lasso_selection(self):
        if len(self._lasso_points) < 3:
            self._lasso_points.clear()
            return

        doc = self.manager.document
        # Rasterize to pixel mask and remember polygon points for later moves
        self.selection_pixels = self._rasterize_polygon(self._lasso_points, doc.width, doc.height)

        if self.selection_pixels:
            self._selection_type = 'lasso'
            self._last_lasso_points = list(self._lasso_points)
            if self.manager.canvas_scene:
                if hasattr(self.manager.canvas_scene, 'set_selection_polygon'):
                    self.manager.canvas_scene.set_selection_polygon(list(self._last_lasso_points))
                else:
                    xs = [p[0] for p in self.selection_pixels]
                    ys = [p[1] for p in self.selection_pixels]
                    self.manager.canvas_scene.set_selection_rect(
                        QRectF(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
                    )

        # keep last_lasso_points for move operations, but clear transient points
        self._lasso_points.clear()

    def _finalize_circle_selection(self, x: int, y: int):
        # Create circular selection using center saved on press.
        # Use polygon approximation and test pixel centers against the
        # polygon so the selection mask matches the visual preview.
        cx, cy = getattr(self, '_circle_center', (self._start_x, self._start_y))
        # keep center as floats
        cx = float(cx)
        cy = float(cy)
        r = float(math.hypot(x - cx, y - cy))
        doc = self.manager.document

        # Build polygon approximation (floats)
        pts = []
        steps = max(16, min(96, int(2 * math.pi * max(1.0, r))))
        for i in range(steps):
            theta = 2 * math.pi * i / steps
            fx = cx + r * math.cos(theta)
            fy = cy + r * math.sin(theta)
            pts.append((fx, fy))

        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x_min = max(0, int(math.floor(min(xs))))
        x_max = min(doc.width - 1, int(math.ceil(max(xs))))
        y_min = max(0, int(math.floor(min(ys))))
        y_max = min(doc.height - 1, int(math.ceil(max(ys))))

        sel = set()
        for py in range(y_min, y_max + 1):
            for px in range(x_min, x_max + 1):
                center_x = px + 0.5
                center_y = py + 0.5
                if self._point_in_polygon(center_x, center_y, pts):
                    sel.add((px, py))

        self.selection_pixels = sel
        # remember circle parameters and show polygon preview if possible
        self._selection_type = 'circle'
        self._last_circle_center = (cx, cy)
        self._last_circle_radius = r
        if self.selection_pixels and self.manager.canvas_scene:
            if hasattr(self.manager.canvas_scene, 'set_selection_polygon'):
                self.manager.canvas_scene.set_selection_polygon(list(pts))
            else:
                xs2 = [p[0] for p in self.selection_pixels]
                ys2 = [p[1] for p in self.selection_pixels]
                self.manager.canvas_scene.set_selection_rect(
                    QRectF(min(xs2), min(ys2), max(xs2) - min(xs2) + 1, max(ys2) - min(ys2) + 1)
                )

        # Cleanup temporary center
        if hasattr(self, '_circle_center'):
            del self._circle_center

    @staticmethod
    def _rasterize_polygon(points: List[Tuple[float, float]], max_w: int, max_h: int) -> Set[Tuple[int, int]]:
        if not points:
            return set()

        ys_all = [p[1] for p in points]
        min_y = max(0, int(math.floor(min(ys_all))))
        max_y = min(max_h - 1, int(math.ceil(max(ys_all))))

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

    def _point_on_segment(self, x: int, y: int, x1: float, y1: float, x2: float, y2: float) -> bool:
        # Check if point (x,y) lies on segment (x1,y1)-(x2,y2)
        # Use cross-product and bounding-box test
        dx1 = x2 - x1
        dy1 = y2 - y1
        dx2 = x - x1
        dy2 = y - y1
        # cross product
        cross = dx1 * dy2 - dy1 * dx2
        if abs(cross) > 1e-6:
            return False
        if min(x1, x2) - 1e-6 <= x <= max(x1, x2) + 1e-6 and min(y1, y2) - 1e-6 <= y <= max(y1, y2) + 1e-6:
            return True
        return False

    def _point_in_polygon(self, x: int, y: int, poly: List[Tuple[float, float]]) -> bool:
        # Ray-cast algorithm with boundary inclusion
        n = len(poly)
        if n == 0:
            return False
        # Boundary check
        for i in range(n):
            j = (i + 1) % n
            if self._point_on_segment(x, y, poly[i][0], poly[i][1], poly[j][0], poly[j][1]):
                return True

        inside = False
        for i in range(n):
            j = (i + 1) % n
            xi, yi = poly[i]
            xj, yj = poly[j]
            intersect = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 0.0) + xi)
            if intersect:
                inside = not inside
        return inside

    def is_point_selected(self, x: int, y: int) -> bool:
        """Return True if (x,y) is within the current selection (supports rect/lasso/circle)."""
        if not self.selection_pixels:
            return False
        if (x, y) in self.selection_pixels:
            return True
        # additional geometric checks if needed
        # Use pixel center tests for geometric membership to match rasterization
        if self._selection_type == 'lasso' and self._last_lasso_points:
            return self._point_in_polygon(x + 0.5, y + 0.5, self._last_lasso_points)
        if self._selection_type == 'circle' and self._last_circle_center is not None and self._last_circle_radius is not None:
            cx, cy = self._last_circle_center
            r = self._last_circle_radius
            return (x + 0.5 - cx) * (x + 0.5 - cx) + (y + 0.5 - cy) * (y + 0.5 - cy) <= r * r
        # fallback
        return False

    # --- Taşıma ---
    def _execute_move(self, dx: int, dy: int):
        doc = self.manager.document
        layer_idx = doc.active_layer_index
        if layer_idx < 0 or layer_idx >= len(doc.layers):
            return

        layer = doc.layers[layer_idx]
        # Use the snapshot of pixels captured at move-start when available
        base_pixels = self._move_orig_selection_pixels if self._move_orig_selection_pixels is not None else self.selection_pixels
        if self._debug_move:
            try:
                if base_pixels:
                    xs = [p[0] for p in base_pixels]
                    ys = [p[1] for p in base_pixels]
                    base_bbox = (min(xs), min(ys), max(xs), max(ys))
                else:
                    base_bbox = None
            except Exception:
                base_bbox = None
            print(f"[selection-debug] execute_move base_count={len(base_pixels) if base_pixels else 0} base_bbox={base_bbox} dx={dx} dy={dy}")
        pixels_to_move = {}
        for (px, py) in base_pixels:
            if doc.in_bounds(px, py):
                c = layer.get_pixel(px, py)
                pixels_to_move[(px, py)] = c if not c.is_transparent else None

        if not pixels_to_move:
            return

        cmd = MoveSelectionCommand(doc, doc.active_frame_index, layer_idx, pixels_to_move, dx, dy)
        self.manager.commit_command(cmd)

        # Seçim alanını da taşı ve orijinal şekli koru
        new_sel = set()
        for (px, py) in base_pixels:
            new_sel.add((px + dx, py + dy))
        # clamp to document bounds
        doc_w, doc_h = doc.width, doc.height
        clamped = set()
        for (px, py) in new_sel:
            if 0 <= px < doc_w and 0 <= py < doc_h:
                clamped.add((px, py))
        self.selection_pixels = clamped
        if self._debug_move:
            try:
                if self.selection_pixels:
                    xs2 = [p[0] for p in self.selection_pixels]
                    ys2 = [p[1] for p in self.selection_pixels]
                    new_bbox = (min(xs2), min(ys2), max(xs2), max(ys2))
                else:
                    new_bbox = None
            except Exception:
                new_bbox = None
            print(f"[selection-debug] execute_move committed new_count={len(self.selection_pixels)} new_bbox={new_bbox}")

        if not self.manager.canvas_scene:
            return

        # Preserve the original visual selection type if available
        if self._selection_type == 'lasso' and (self._move_orig_last_lasso_points or self._last_lasso_points):
            src = self._move_orig_last_lasso_points if self._move_orig_last_lasso_points is not None else self._last_lasso_points
            shifted = [(x + dx, y + dy) for (x, y) in src]
            self._last_lasso_points = shifted
            if hasattr(self.manager.canvas_scene, 'set_selection_polygon'):
                self.manager.canvas_scene.set_selection_polygon(shifted)
            else:
                xs = [p[0] for p in self.selection_pixels]
                ys = [p[1] for p in self.selection_pixels]
                self.manager.canvas_scene.set_selection_rect(
                    QRectF(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
                )
        elif self._selection_type == 'circle' and (self._move_orig_circle_center is not None or self._last_circle_center is not None) and (self._move_orig_circle_radius is not None or self._last_circle_radius is not None):
            cx, cy = self._move_orig_circle_center if self._move_orig_circle_center is not None else self._last_circle_center
            r = self._move_orig_circle_radius if self._move_orig_circle_radius is not None else self._last_circle_radius
            ncx, ncy = cx + dx, cy + dy
            self._last_circle_center = (ncx, ncy)
            if hasattr(self.manager.canvas_scene, 'set_selection_polygon'):
                pts = []
                steps = max(16, min(48, int(2 * math.pi * max(1, r))))
                for i in range(steps):
                    theta = 2 * math.pi * i / steps
                    fx = ncx + r * math.cos(theta)
                    fy = ncy + r * math.sin(theta)
                    pts.append((fx, fy))
                self.manager.canvas_scene.set_selection_polygon(pts)
            else:
                xs = [p[0] for p in self.selection_pixels]
                ys = [p[1] for p in self.selection_pixels]
                self.manager.canvas_scene.set_selection_rect(
                    QRectF(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
                )
        else:
            # fallback: show bounding rect
            if self.selection_pixels:
                xs = [p[0] for p in self.selection_pixels]
                ys = [p[1] for p in self.selection_pixels]
                self.manager.canvas_scene.set_selection_rect(
                    QRectF(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
                )
        # Update _last_rect for rect-type selections so subsequent moves
        # start from the correct (new) position, not the original.
        if self._selection_type == 'rect' and self.selection_pixels:
            xs_r = [p[0] for p in self.selection_pixels]
            ys_r = [p[1] for p in self.selection_pixels]
            self._last_rect = (min(xs_r), min(ys_r), max(xs_r), max(ys_r))
        # Clear move snapshots after executing move to avoid stale state
        self._move_orig_selection_pixels = None
        self._move_orig_last_lasso_points = None
        self._move_orig_circle_center = None
        self._move_orig_circle_radius = None
        # Clear any preview mask shown during drag
        if self.manager and getattr(self.manager, 'canvas_scene', None):
            try:
                self.manager.canvas_scene.set_preview_selection_mask(None)
            except Exception:
                pass

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

        cmd = PasteCommand(doc, doc.active_frame_index, layer_idx, dict(self.clipboard), offset_x, offset_y)
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
            cmd = DeleteSelectionCommand(doc, doc.active_frame_index, layer_idx, pixels)
            self.manager.commit_command(cmd)

    def clear_selection(self):
        self.selection_pixels.clear()
        self._clear_scene_selection()

    def _clear_scene_selection(self):
        if self.manager and self.manager.canvas_scene:
            self.manager.canvas_scene.set_selection_rect(None)
            if hasattr(self.manager.canvas_scene, 'set_selection_polygon'):
                self.manager.canvas_scene.set_selection_polygon(None)

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
