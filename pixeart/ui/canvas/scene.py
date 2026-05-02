import math
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsItem
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QTimer, QPointF

from pixeart.core import Document


CHUNK_SIZE = 128


class ChunkItem(QGraphicsItem):
    def __init__(self, chunk_x: int, chunk_y: int, pixel_w: int, pixel_h: int, parent=None):
        super().__init__(parent)
        self.chunk_x = chunk_x
        self.chunk_y = chunk_y
        self.pixel_w = min(CHUNK_SIZE, pixel_w - chunk_x * CHUNK_SIZE)
        self.pixel_h = min(CHUNK_SIZE, pixel_h - chunk_y * CHUNK_SIZE)
        self.image = QImage(self.pixel_w, self.pixel_h, QImage.Format.Format_ARGB32_Premultiplied)
        self.image.fill(Qt.GlobalColor.transparent)
        self.setPos(chunk_x * CHUNK_SIZE, chunk_y * CHUNK_SIZE)
        self._dirty = False

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.pixel_w, self.pixel_h)

    def paint(self, painter: QPainter, option, widget=None):
        painter.drawImage(0, 0, self.image)

    def update_pixel(self, local_x: int, local_y: int, color: QColor):
        if 0 <= local_x < self.pixel_w and 0 <= local_y < self.pixel_h:
            self.image.setPixelColor(local_x, local_y, color)
            self.update(QRectF(local_x, local_y, 1, 1))

    def clear(self):
        self.image.fill(Qt.GlobalColor.transparent)
        self.update()


class LayerGraphicsItem:
    def __init__(self, width: int, height: int, scene: QGraphicsScene):
        self.width = width
        self.height = height
        self._scene = scene
        self._chunks = {}
        self._visible = True
        self._opacity = 1.0

        cols = (width + CHUNK_SIZE - 1) // CHUNK_SIZE
        rows = (height + CHUNK_SIZE - 1) // CHUNK_SIZE
        for cy in range(rows):
            for cx in range(cols):
                chunk = ChunkItem(cx, cy, width, height)
                self._chunks[(cx, cy)] = chunk
                scene.addItem(chunk)

    def set_z_value(self, z: float):
        for chunk in self._chunks.values():
            chunk.setZValue(z)

    def set_visible(self, visible: bool):
        self._visible = visible
        for chunk in self._chunks.values():
            chunk.setVisible(visible)

    def set_opacity(self, opacity: float):
        self._opacity = opacity
        for chunk in self._chunks.values():
            chunk.setOpacity(opacity)

    def update_pixel(self, x: int, y: int, color: QColor):
        cx, cy = x // CHUNK_SIZE, y // CHUNK_SIZE
        chunk = self._chunks.get((cx, cy))
        if chunk:
            chunk.update_pixel(x % CHUNK_SIZE, y % CHUNK_SIZE, color)

    def clear(self):
        for chunk in self._chunks.values():
            chunk.clear()

    def remove_from_scene(self):
        for chunk in self._chunks.values():
            self._scene.removeItem(chunk)
        self._chunks.clear()


class CanvasScene(QGraphicsScene):
    pixel_clicked = pyqtSignal(int, int, Qt.MouseButton)
    pixel_dragged = pyqtSignal(int, int, Qt.MouseButton)
    pixel_released = pyqtSignal(int, int, Qt.MouseButton)
    color_picked = pyqtSignal(QColor)
    # Float-precision signals for tools that need sub-pixel accuracy
    pixel_clicked_f = pyqtSignal(float, float, Qt.MouseButton)
    pixel_dragged_f = pyqtSignal(float, float, Qt.MouseButton)
    pixel_released_f = pyqtSignal(float, float, Qt.MouseButton)

    def __init__(self, document: Document = None, parent=None):
        super().__init__(parent)
        self.document = document
        self.layer_items = []
        self.onion_items = []
        self._reference_item = None
        self._onion_enabled = False
        self._onion_opacity = 0.3
        self._selection_rect = None
        self._selection_polygon = None
        self._preview_selection_mask = None
        self._ants_offset = 0
        self._ants_timer = QTimer()
        self._ants_timer.timeout.connect(self._advance_ants)
        self._setup_checkerboard_background()
        self.show_layer_edges = False
        self.show_selection_edges = True

        if self.document:
            self.setSceneRect(0, 0, document.width, document.height)
            self.sync_layers()

    def set_document(self, document: Document):
        self.document = document
        self.setSceneRect(0, 0, document.width, document.height)
        self.sync_layers()

    def _setup_checkerboard_background(self):
        checker_size = 8
        pm = QPixmap(checker_size * 2, checker_size * 2)
        pm.fill(QColor("#3a3a3a"))
        painter = QPainter(pm)
        painter.fillRect(0, 0, checker_size, checker_size, QColor("#454545"))
        painter.fillRect(checker_size, checker_size, checker_size, checker_size, QColor("#454545"))
        painter.end()
        self.checker_brush = QBrush(pm)

    def drawBackground(self, painter: QPainter, rect: QRectF):
        if self.document:
            scene_rect = self.sceneRect()
            painter.fillRect(scene_rect, self.checker_brush)

    def sync_layers(self):
        for item in self.layer_items:
            item.remove_from_scene()
        self.layer_items.clear()
        
        for item in self.onion_items:
            item.remove_from_scene()
        self.onion_items.clear()

        if not self.document:
            return

        active_idx = self.document.active_layer_index

        # 1. Onion Skinning (Previous Frame)
        if self._onion_enabled and self.document.frames:
            current_frame_idx = self.document.active_frame_index
            if current_frame_idx > 0:
                prev_frame = self.document.frames[current_frame_idx - 1]
                for core_layer in prev_frame.layers:
                    if core_layer.is_visible:
                        ui_layer = LayerGraphicsItem(self.document.width, self.document.height, self)
                        ui_layer.set_z_value(-2) # En altta
                        ui_layer.set_opacity(self._onion_opacity)
                        for (x, y), core_color in core_layer.active_pixels.items():
                            qt_color = QColor(*core_color.to_rgba_tuple())
                            ui_layer.update_pixel(x, y, qt_color)
                        self.onion_items.append(ui_layer)
            
            if current_frame_idx < len(self.document.frames) - 1:
                next_frame = self.document.frames[current_frame_idx + 1]
                for core_layer in next_frame.layers:
                    if core_layer.is_visible:
                        ui_layer = LayerGraphicsItem(self.document.width, self.document.height, self)
                        ui_layer.set_z_value(-1) # En alttan bir üstte
                        ui_layer.set_opacity(self._onion_opacity)
                        for (x, y), core_color in core_layer.active_pixels.items():
                            qt_color = QColor(*core_color.to_rgba_tuple())
                            ui_layer.update_pixel(x, y, qt_color)
                        self.onion_items.append(ui_layer)

        # 2. Current Frame Layers
        for i, core_layer in enumerate(self.document.layers):
            ui_layer = LayerGraphicsItem(self.document.width, self.document.height, self)
            ui_layer.set_z_value(i)
            ui_layer.set_visible(core_layer.is_visible)

            for (x, y), core_color in core_layer.active_pixels.items():
                qt_color = QColor(*core_color.to_rgba_tuple())
                ui_layer.update_pixel(x, y, qt_color)

            self.layer_items.append(ui_layer)

    def set_onion_skinning(self, enabled: bool):
        self._onion_enabled = enabled
        self.sync_layers()

    def draw_pixel(self, x: int, y: int, qt_color: QColor):
        active_idx = self.document.active_layer_index
        if active_idx < 0 or active_idx >= len(self.layer_items):
            return
        self.layer_items[active_idx].update_pixel(x, y, qt_color)

    # --- Selection overlay ---
    def set_selection_rect(self, rect):
        self._selection_rect = rect
        # clear polygon preview when rect is set
        if rect is not None:
            self._selection_polygon = None
        if rect and not self._ants_timer.isActive():
            self._ants_timer.start(150)
        elif not rect:
            self._ants_timer.stop()
        self.update()

    def set_selection_polygon(self, points: list):
        """Set polygon preview for lasso selection. Points is a list of (x,y) tuples."""
        if points:
            self._selection_polygon = [QPointF(x, y) for (x, y) in points]
            if not self._ants_timer.isActive():
                self._ants_timer.start(150)
        else:
            self._selection_polygon = None
            if not self._selection_rect and self._ants_timer.isActive():
                self._ants_timer.stop()
        self.update()

    def set_preview_selection_mask(self, mask: set):
        """Set a temporary selection mask used for live-preview during moves.
        Pass None to clear."""
        if mask:
            self._preview_selection_mask = set(mask)
            if not self._ants_timer.isActive():
                self._ants_timer.start(150)
            # debug log: bbox and size
            try:
                xs = [p[0] for p in self._preview_selection_mask]
                ys = [p[1] for p in self._preview_selection_mask]
                bbox = (min(xs), min(ys), max(xs), max(ys)) if xs and ys else None
            except Exception:
                bbox = None
            print(f"[canvas-debug] preview_mask set count={len(self._preview_selection_mask)} bbox={bbox}")
        else:
            self._preview_selection_mask = None
            if not self._selection_rect and not self._selection_polygon and self._ants_timer.isActive():
                self._ants_timer.stop()
        self.update()

    def _advance_ants(self):
        self._ants_offset = (self._ants_offset + 2) % 16
        self.update()

    def _point_on_segment_local(self, x: float, y: float, a: tuple, b: tuple) -> bool:
        x1, y1 = a
        x2, y2 = b
        dx1 = x2 - x1
        dy1 = y2 - y1
        dx2 = x - x1
        dy2 = y - y1
        cross = dx1 * dy2 - dy1 * dx2
        if abs(cross) > 1e-6:
            return False
        if min(x1, x2) - 1e-6 <= x <= max(x1, x2) + 1e-6 and min(y1, y2) - 1e-6 <= y <= max(y1, y2) + 1e-6:
            return True
        return False

    def _point_in_polygon_local(self, x: float, y: float, poly: list) -> bool:
        n = len(poly)
        if n == 0:
            return False
        for i in range(n):
            j = (i + 1) % n
            if self._point_on_segment_local(x, y, poly[i], poly[j]):
                return True

        inside = False
        for i in range(n):
            j = (i + 1) % n
            xi, yi = poly[i]
            xj, yj = poly[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 0.0) + xi):
                inside = not inside
        return inside

    def drawForeground(self, painter: QPainter, rect: QRectF):
        # Layer Edges
        if self.show_layer_edges and self.document:
            pen = QPen(QColor(100, 200, 255, 120))
            pen.setWidth(0)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.sceneRect())

        # Selection Edges (karınca sürüsü)
        if self.show_selection_edges:
            # If a preview mask exists (live-drag), draw its edge pixels — this
            # ensures the preview exactly matches the pixel selection mask.
            if self._preview_selection_mask:
                pen = QPen(QColor(255, 255, 255), 0)
                pen.setDashPattern([4, 4])
                pen.setDashOffset(self._ants_offset)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                mask = self._preview_selection_mask
                # draw only edge pixels to mimic selection outline
                for (px, py) in mask:
                    # check 8-neighbors for outside pixel
                    is_edge = False
                    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)):
                        if (px + dx, py + dy) not in mask:
                            is_edge = True
                            break
                    if is_edge:
                        painter.drawRect(px, py, 1, 1)
            elif self._selection_polygon:
                # Draw a semi-transparent filled preview using pixel-center tests
                pts = [(p.x(), p.y()) for p in self._selection_polygon]
                if pts:
                    xs = [p[0] for p in pts]
                    ys = [p[1] for p in pts]
                    x_min = max(0, int(math.floor(min(xs))))
                    x_max = int(math.ceil(max(xs)))
                    y_min = max(0, int(math.floor(min(ys))))
                    y_max = int(math.ceil(max(ys)))

                    painter.save()
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QColor(255, 255, 255, 40))
                    for py in range(y_min, y_max + 1):
                        for px in range(x_min, x_max + 1):
                            cx = px + 0.5
                            cy = py + 0.5
                            if self._point_in_polygon_local(cx, cy, pts):
                                painter.drawRect(px, py, 1, 1)
                    painter.restore()

                pen = QPen(QColor(255, 255, 255), 0)
                pen.setDashPattern([4, 4])
                pen.setDashOffset(self._ants_offset)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPolygon(self._selection_polygon)

                pen2 = QPen(QColor(0, 0, 0), 0)
                pen2.setDashPattern([4, 4])
                pen2.setDashOffset(self._ants_offset + 4)
                painter.setPen(pen2)
                painter.drawPolygon(self._selection_polygon)
            elif self._selection_rect:
                pen = QPen(QColor(255, 255, 255), 0)
                pen.setDashPattern([4, 4])
                pen.setDashOffset(self._ants_offset)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(self._selection_rect)

                pen2 = QPen(QColor(0, 0, 0), 0)
                pen2.setDashPattern([4, 4])
                pen2.setDashOffset(self._ants_offset + 4)
                painter.setPen(pen2)
                painter.drawRect(self._selection_rect)

    # --- Reference image ---
    def set_reference_image(self, path: str):
        from pixeart.ui.canvas.reference_layer import ReferenceLayerItem
        self.clear_reference_image()
        self._reference_item = ReferenceLayerItem(path)
        self.addItem(self._reference_item)

    def clear_reference_image(self):
        if self._reference_item:
            self.removeItem(self._reference_item)
            self._reference_item = None

    # --- Mouse events ---
    def mousePressEvent(self, event):
        if not self.document:
            super().mousePressEvent(event)
            return
            
        pos = event.scenePos()
        x_f, y_f = pos.x(), pos.y()
        x, y = int(x_f), int(y_f)
        
        if getattr(self, "picking_target_color", False):
            if self.document.in_bounds(x, y):
                # En üstteki görünür katmandan rengi al
                picked = QColor(0, 0, 0, 0)
                for layer in reversed(self.document.layers):
                    if layer.is_visible:
                        c = layer.get_pixel(x, y)
                        if not c.is_transparent:
                            picked = QColor(c.r, c.g, c.b, c.a)
                            break
                self.color_picked.emit(picked)
            return
            
        if self.document.in_bounds(x, y):
            # emit both integer and float coordinates
            self.pixel_clicked.emit(x, y, event.button())
            try:
                self.pixel_clicked_f.emit(x_f, y_f, event.button())
            except Exception:
                pass
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self.document:
            super().mouseMoveEvent(event)
            return
        if event.buttons() & Qt.MouseButton.LeftButton:
            btn = Qt.MouseButton.LeftButton
        elif event.buttons() & Qt.MouseButton.RightButton:
            btn = Qt.MouseButton.RightButton
        else:
            super().mouseMoveEvent(event)
            return
        pos = event.scenePos()
        x_f, y_f = pos.x(), pos.y()
        x, y = int(x_f), int(y_f)
        if self.document.in_bounds(x, y):
            self.pixel_dragged.emit(x, y, btn)
            try:
                self.pixel_dragged_f.emit(x_f, y_f, btn)
            except Exception:
                pass
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if not self.document:
            super().mouseReleaseEvent(event)
            return
        pos = event.scenePos()
        x_f, y_f = pos.x(), pos.y()
        x, y = int(x_f), int(y_f)
        self.pixel_released.emit(x, y, event.button())
        try:
            self.pixel_released_f.emit(x_f, y_f, event.button())
        except Exception:
            pass
        super().mouseReleaseEvent(event)
