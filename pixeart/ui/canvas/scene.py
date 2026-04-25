from PyQt6.QtWidgets import QGraphicsScene, QGraphicsItem
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QBrush
from PyQt6.QtCore import Qt, QRectF, pyqtSignal

from pixeart.core import Document

class LayerGraphicsItem(QGraphicsItem):
    def __init__(self, width: int, height: int, parent=None):
        super().__init__(parent)
        self.width = width
        self.height = height
        self.image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        self.image.fill(Qt.GlobalColor.transparent)
        
    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter: QPainter, option, widget=None):
        painter.drawImage(0, 0, self.image)

    def update_pixel(self, x: int, y: int, color: QColor):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.image.setPixelColor(x, y, color)
            self.update(QRectF(x, y, 1, 1))
            
    def clear(self):
        self.image.fill(Qt.GlobalColor.transparent)
        self.update()


class CanvasScene(QGraphicsScene):
    pixel_clicked = pyqtSignal(int, int, Qt.MouseButton)
    pixel_dragged = pyqtSignal(int, int, Qt.MouseButton)
    pixel_released = pyqtSignal(int, int, Qt.MouseButton)
    
    def __init__(self, document: Document = None, parent=None):
        super().__init__(parent)
        self.document = document
        self.layer_items = []
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
        # Viewport arka planını view.py yapıyor, biz sadece tuvalin içini boyayacağız
        if self.document:
            scene_rect = self.sceneRect()
            painter.fillRect(scene_rect, self.checker_brush)

    def sync_layers(self):
        for item in self.layer_items:
            self.removeItem(item)
        self.layer_items.clear()
        
        if not self.document:
            return
        
        for i, core_layer in enumerate(self.document.layers):
            ui_layer = LayerGraphicsItem(self.document.width, self.document.height)
            ui_layer.setZValue(i)
            ui_layer.setVisible(core_layer.is_visible)
            
            for (x, y), core_color in core_layer.active_pixels.items():
                qt_color = QColor(*core_color.to_rgba_tuple())
                ui_layer.image.setPixelColor(x, y, qt_color)
                
            self.addItem(ui_layer)
            self.layer_items.append(ui_layer)

    def draw_pixel(self, x: int, y: int, qt_color: QColor):
        active_idx = self.document.active_layer_index
        if active_idx < 0 or active_idx >= len(self.layer_items):
            return
            
        ui_layer = self.layer_items[active_idx]
        ui_layer.update_pixel(x, y, qt_color)

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
            
        # Left or Right button drag
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
