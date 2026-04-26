from PyQt6.QtWidgets import QGraphicsPixmapItem, QGraphicsItem
from PyQt6.QtGui import QPixmap


class ReferenceLayerItem(QGraphicsPixmapItem):
    def __init__(self, image_path: str, parent=None):
        pixmap = QPixmap(image_path)
        super().__init__(pixmap, parent)
        self.image_path = image_path
        self.setOpacity(0.4)
        self.setZValue(-100)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
