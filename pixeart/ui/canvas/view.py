import math
from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtCore import Qt, QPoint, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QMouseEvent, QWheelEvent, QKeyEvent, QPen, QColor, QTransform


class CanvasView(QGraphicsView):
    zoom_changed = pyqtSignal(float)

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

        self.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

        self._zoom_factor = 1.0
        self._zoom_step = 1.15

        self._is_panning = False
        self._pan_start_pos = QPoint()
        self._space_pressed = False

        # Grid ayarları
        self._show_grid = True
        self._grid_color = QColor(150, 150, 150, 80)
        self._show_tile_grid = True
        self._tile_size = 16
        self._tile_grid_color = QColor(80, 180, 255, 100)

        # Simetri ekseni
        self._symmetry_mode = "none"

        # Snap & Tiled
        self.snap_to_grid = False
        self._tiled_mode = "none"

        self.setBackgroundBrush(QColor("#1e1e1e"))

    # --- Grid property'leri ---
    def set_grid_visible(self, visible: bool):
        self._show_grid = visible
        self.viewport().update()

    def set_grid_color(self, color: QColor):
        self._grid_color = color
        self.viewport().update()

    def set_tile_grid_visible(self, visible: bool):
        self._show_tile_grid = visible
        self.viewport().update()

    def set_tile_size(self, size: int):
        self._tile_size = max(2, size)
        self.viewport().update()

    def set_tile_grid_color(self, color: QColor):
        self._tile_grid_color = color
        self.viewport().update()

    def set_symmetry_mode(self, mode: str):
        self._symmetry_mode = mode
        self.viewport().update()

    def set_tiled_mode(self, mode: str):
        """Döşeme modunu ayarla: 'none', 'x', 'y', 'both'"""
        self._tiled_mode = mode
        self.viewport().update()

    # --- Zoom ---
    def set_zoom(self, scale_factor: float):
        scale_factor = max(0.1, min(scale_factor, 100.0))
        transform = QTransform()
        transform.scale(scale_factor, scale_factor)
        self.setTransform(transform)
        self._zoom_factor = scale_factor
        self.zoom_changed.emit(self._zoom_factor * 100)

    def reset_view(self):
        if not self.scene() or not self.scene().sceneRect().isValid():
            self.set_zoom(1.0)
            return

        rect = self.scene().sceneRect()
        view_rect = self.viewport().rect()

        scale_x = (view_rect.width() * 0.8) / rect.width() if rect.width() > 0 else 1.0
        scale_y = (view_rect.height() * 0.8) / rect.height() if rect.height() > 0 else 1.0

        ideal_scale = min(scale_x, scale_y)
        ideal_scale = max(1.0, ideal_scale)

        self.set_zoom(ideal_scale)
        self.centerOn(rect.center())

    def wheelEvent(self, event: QWheelEvent):
        scene_pos_before = self.mapToScene(event.position().toPoint())

        if event.angleDelta().y() > 0:
            new_zoom = self._zoom_factor * self._zoom_step
        else:
            new_zoom = self._zoom_factor / self._zoom_step

        self.set_zoom(new_zoom)

        scene_pos_after = self.mapToScene(event.position().toPoint())
        diff = scene_pos_before - scene_pos_after

        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + int(diff.x() * self._zoom_factor))
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() + int(diff.y() * self._zoom_factor))
        event.accept()

    # --- Panning ---
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_pressed = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_pressed = False
            if not self._is_panning:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton or (event.button() == Qt.MouseButton.LeftButton and self._space_pressed):
            self._is_panning = True
            self._pan_start_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_panning:
            current_pos = event.position().toPoint()
            delta = current_pos - self._pan_start_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self._pan_start_pos = current_pos
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton or (event.button() == Qt.MouseButton.LeftButton and self._is_panning):
            self._is_panning = False
            self.setCursor(Qt.CursorShape.OpenHandCursor if self._space_pressed else Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # --- Foreground: Grid + Simetri Ekseni ---
    def drawForeground(self, painter: QPainter, rect: QRectF):
        super().drawForeground(painter, rect)

        scene_rect = self.sceneRect()
        if not scene_rect.isValid():
            return

        left = max(int(math.floor(rect.left())), int(scene_rect.left()))
        right = min(int(math.ceil(rect.right())), int(scene_rect.right()))
        top = max(int(math.floor(rect.top())), int(scene_rect.top()))
        bottom = min(int(math.ceil(rect.bottom())), int(scene_rect.bottom()))

        # Tile grid (daha düşük zoom seviyesinde de görünür)
        if self._show_tile_grid and self._zoom_factor >= 4.0:
            ts = self._tile_size
            pen = QPen(self._tile_grid_color)
            pen.setWidth(0)
            painter.setPen(pen)

            start_x = (left // ts) * ts
            for x in range(start_x, right + 1, ts):
                if int(scene_rect.left()) <= x <= int(scene_rect.right()):
                    painter.drawLine(x, top, x, bottom)

            start_y = (top // ts) * ts
            for y in range(start_y, bottom + 1, ts):
                if int(scene_rect.top()) <= y <= int(scene_rect.bottom()):
                    painter.drawLine(left, y, right, y)

        # Piksel grid (yüksek zoom seviyesi)
        if self._show_grid and self._zoom_factor >= 8.0:
            pen = QPen(self._grid_color)
            pen.setWidth(0)
            painter.setPen(pen)

            for x in range(left, right + 1):
                painter.drawLine(x, top, x, bottom)
            for y in range(top, bottom + 1):
                painter.drawLine(left, y, right, y)

        # Simetri ekseni çizgileri
        if self._symmetry_mode != "none":
            from PyQt6.QtCore import QPointF
            pen = QPen(QColor(255, 50, 80, 180))
            pen.setWidth(0)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)

            sw = scene_rect.width()
            sh = scene_rect.height()
            sl = scene_rect.left()
            st = scene_rect.top()

            if self._symmetry_mode in ("vertical", "both"):
                mid_x = sl + sw / 2.0
                painter.drawLine(QPointF(mid_x, st), QPointF(mid_x, st + sh))

            if self._symmetry_mode in ("horizontal", "both"):
                mid_y = st + sh / 2.0
                painter.drawLine(QPointF(sl, mid_y), QPointF(sl + sw, mid_y))
