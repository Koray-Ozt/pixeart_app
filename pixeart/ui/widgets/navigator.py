from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QImage, QPixmap, QPen, QMouseEvent


class NavigatorWidget(QWidget):
    def __init__(self, canvas_view=None, canvas_scene=None, parent=None):
        super().__init__(parent)
        self._canvas_view = canvas_view
        self._canvas_scene = canvas_scene
        self._preview = QPixmap()
        self._viewport_rect = QRectF()
        self._doc_width = 0
        self._doc_height = 0
        self.setMinimumSize(160, 120)
        self.setMaximumHeight(200)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_canvas(self, canvas_view, canvas_scene):
        self._canvas_view = canvas_view
        self._canvas_scene = canvas_scene

    def update_preview(self):
        if not self._canvas_scene or not self._canvas_scene.document:
            self._preview = QPixmap()
            self.update()
            return

        doc = self._canvas_scene.document
        self._doc_width = doc.width
        self._doc_height = doc.height

        img = QImage(doc.width, doc.height, QImage.Format.Format_ARGB32)
        img.fill(QColor(30, 30, 30))

        for layer in doc.layers:
            if not layer.is_visible:
                continue
            for (x, y), color in layer.active_pixels.items():
                if not color.is_transparent:
                    img.setPixelColor(x, y, QColor(*color.to_rgba_tuple()))

        self._preview = QPixmap.fromImage(img)
        self._update_viewport_rect()
        self.update()

    def _update_viewport_rect(self):
        if not self._canvas_view or self._doc_width <= 0:
            self._viewport_rect = QRectF()
            return

        tl = self._canvas_view.mapToScene(0, 0)
        br = self._canvas_view.mapToScene(
            self._canvas_view.viewport().width(),
            self._canvas_view.viewport().height()
        )
        self._viewport_rect = QRectF(tl, br)
        self.update()

    def _get_draw_rect(self):
        w, h = self.width() - 8, self.height() - 8
        if self._doc_width <= 0 or self._doc_height <= 0:
            return QRectF(4, 4, w, h), 1.0

        scale = min(w / self._doc_width, h / self._doc_height)
        pw = self._doc_width * scale
        ph = self._doc_height * scale
        ox = (self.width() - pw) / 2
        oy = (self.height() - ph) / 2
        return QRectF(ox, oy, pw, ph), scale

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        p.fillRect(self.rect(), QColor(25, 25, 30))

        draw_rect, scale = self._get_draw_rect()

        if not self._preview.isNull():
            p.drawPixmap(draw_rect.toRect(), self._preview)

        # Viewport çerçevesi
        if not self._viewport_rect.isNull() and self._doc_width > 0:
            vr = QRectF(
                draw_rect.x() + self._viewport_rect.x() * scale,
                draw_rect.y() + self._viewport_rect.y() * scale,
                self._viewport_rect.width() * scale,
                self._viewport_rect.height() * scale
            )
            pen = QPen(QColor(255, 60, 60, 200), 2)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(vr)

        p.end()

    def mousePressEvent(self, event: QMouseEvent):
        self._navigate_to(event.position())
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._navigate_to(event.position())
        event.accept()

    def _navigate_to(self, pos):
        if not self._canvas_view or self._doc_width <= 0:
            return

        draw_rect, scale = self._get_draw_rect()
        if scale <= 0:
            return

        scene_x = (pos.x() - draw_rect.x()) / scale
        scene_y = (pos.y() - draw_rect.y()) / scale

        self._canvas_view.centerOn(QPointF(scene_x, scene_y))
        self._update_viewport_rect()
