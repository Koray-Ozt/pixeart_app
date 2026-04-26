from PyQt6.QtWidgets import QGraphicsScene, QGraphicsItem
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QTimer

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

    def __init__(self, document: Document = None, parent=None):
        super().__init__(parent)
        self.document = document
        self.layer_items = []
        self._reference_item = None
        self._onion_enabled = False
        self._onion_opacity = 0.3
        self._selection_rect = None
        self._ants_offset = 0
        self._ants_timer = QTimer()
        self._ants_timer.timeout.connect(self._advance_ants)
        self._setup_checkerboard_background()

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
        pm.fill(QColor("#ffffff"))
        painter = QPainter(pm)
        painter.fillRect(0, 0, checker_size, checker_size, QColor("#cccccc"))
        painter.fillRect(checker_size, checker_size, checker_size, checker_size, QColor("#cccccc"))
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

        if not self.document:
            return

        active_idx = self.document.active_layer_index

        for i, core_layer in enumerate(self.document.layers):
            ui_layer = LayerGraphicsItem(self.document.width, self.document.height, self)
            ui_layer.set_z_value(i)
            ui_layer.set_visible(core_layer.is_visible)

            # Onion skinning
            if self._onion_enabled and core_layer.is_visible:
                if i == active_idx:
                    ui_layer.set_opacity(1.0)
                elif abs(i - active_idx) == 1:
                    ui_layer.set_opacity(self._onion_opacity)
                else:
                    ui_layer.set_opacity(1.0)

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
        if rect and not self._ants_timer.isActive():
            self._ants_timer.start(150)
        elif not rect:
            self._ants_timer.stop()
        self.update()

    def _advance_ants(self):
        self._ants_offset = (self._ants_offset + 2) % 16
        self.update()

    def drawForeground(self, painter: QPainter, rect: QRectF):
        if self._selection_rect:
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
        x, y = int(pos.x()), int(pos.y())
        if self.document.in_bounds(x, y):
            self.pixel_clicked.emit(x, y, event.button())
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
        x, y = int(pos.x()), int(pos.y())
        if self.document.in_bounds(x, y):
            self.pixel_dragged.emit(x, y, btn)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if not self.document:
            super().mouseReleaseEvent(event)
            return
        pos = event.scenePos()
        x, y = int(pos.x()), int(pos.y())
        self.pixel_released.emit(x, y, event.button())
        super().mouseReleaseEvent(event)
