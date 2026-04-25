from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtCore import Qt, QPoint, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QMouseEvent, QWheelEvent, QKeyEvent, QPen, QColor, QTransform
import math

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
        
        self.setBackgroundBrush(QColor("#1e1e1e"))

    def set_zoom(self, scale_factor: float):
        scale_factor = max(0.1, min(scale_factor, 100.0))
        transform = QTransform()
        transform.scale(scale_factor, scale_factor)
        self.setTransform(transform)
        self._zoom_factor = scale_factor
        self.zoom_changed.emit(self._zoom_factor * 100)
        
    def reset_view(self):
        """Kamerayı sıfırlar ve sahneyi merkeze alır, otomatik zoom yapar."""
        if not self.scene() or not self.scene().sceneRect().isValid():
            self.set_zoom(1.0)
            return
            
        rect = self.scene().sceneRect()
        view_rect = self.viewport().rect()
        
        # %80'ini kaplayacak şekilde ölçekle
        scale_x = (view_rect.width() * 0.8) / rect.width() if rect.width() > 0 else 1.0
        scale_y = (view_rect.height() * 0.8) / rect.height() if rect.height() > 0 else 1.0
        
        # Enstantane bozulmasını engellemek için min scale al
        ideal_scale = min(scale_x, scale_y)
        ideal_scale = max(1.0, ideal_scale) # En az 1x olsun
        
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
    
    def drawForeground(self, painter: QPainter, rect: QRectF):
        super().drawForeground(painter, rect)
        
        if self._zoom_factor < 8.0:
            return
            
        left = int(math.floor(rect.left()))
        right = int(math.ceil(rect.right()))
        top = int(math.floor(rect.top()))
        bottom = int(math.ceil(rect.bottom()))
        
        scene_rect = self.sceneRect()
        left = max(left, int(scene_rect.left()))
        right = min(right, int(scene_rect.right()))
        top = max(top, int(scene_rect.top()))
        bottom = min(bottom, int(scene_rect.bottom()))
        
        pen = QPen(QColor(150, 150, 150, 80))
        pen.setWidth(0)
        painter.setPen(pen)
        
        for x in range(left, right + 1):
            painter.drawLine(x, top, x, bottom)
            
        for y in range(top, bottom + 1):
            painter.drawLine(left, y, right, y)
