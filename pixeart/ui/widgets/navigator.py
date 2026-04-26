from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QRectF, QPointF, QRect
from PyQt6.QtGui import QPainter, QColor, QImage, QPixmap, QPen, QMouseEvent, QBrush


class NavigatorWidget(QWidget):
    """
    Yüksek çözünürlüklü navigator önizlemesi.
    Belgenin piksellerini widget'ın gerçek fiziksel piksel boyutuna
    nearest-neighbor (piksel sanatına uygun) ölçekleme ile çizer.
    Kırmızı çerçeve, ana tuvalin bakış açısını takip eder.
    """

    def __init__(self, canvas_view=None, canvas_scene=None, parent=None):
        super().__init__(parent)
        self._canvas_view = canvas_view
        self._canvas_scene = canvas_scene
        self._preview = QPixmap()
        self._viewport_rect = QRectF()
        self._doc_width = 0
        self._doc_height = 0
        self.setMinimumSize(200, 150)
        self.setMaximumHeight(250)
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

        # --- Yüksek çözünürlüklü render ---
        # Widget'ın gerçek boyutuna göre ölçekleme faktörü hesapla.
        # Önizleme, widget'ın iç alanına (padding hariç) sığacak şekilde
        # tam sayı katı (nearest-neighbor) olarak ölçeklenir.
        draw_rect, _ = self._get_draw_rect()
        target_w = max(int(draw_rect.width()), 1)
        target_h = max(int(draw_rect.height()), 1)

        # Nearest-neighbor ölçekleme faktörü (tam sayı veya kesirli)
        scale_x = target_w / max(doc.width, 1)
        scale_y = target_h / max(doc.height, 1)
        pixel_scale = min(scale_x, scale_y)
        pixel_scale = max(pixel_scale, 1.0)

        render_w = int(doc.width * pixel_scale)
        render_h = int(doc.height * pixel_scale)

        # Checkerboard arka plan
        img = QImage(render_w, render_h, QImage.Format.Format_ARGB32_Premultiplied)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)

        checker_size = max(int(pixel_scale), 4)
        c1, c2 = QColor(200, 200, 200), QColor(255, 255, 255)
        for cy in range(0, render_h, checker_size):
            for cx in range(0, render_w, checker_size):
                color = c1 if ((cx // checker_size) + (cy // checker_size)) % 2 == 0 else c2
                painter.fillRect(QRect(cx, cy, checker_size, checker_size), color)

        # Pikselleri çiz — her piksel pixel_scale x pixel_scale kare olarak
        ps = int(max(pixel_scale, 1))
        for layer in doc.layers:
            if not layer.is_visible:
                continue
            for (x, y), color in layer.active_pixels.items():
                if color.is_transparent:
                    continue
                qc = QColor(color.r, color.g, color.b, color.a)
                rx = int(x * pixel_scale)
                ry = int(y * pixel_scale)
                painter.fillRect(QRect(rx, ry, ps, ps), qc)

        painter.end()

        self._preview = QPixmap.fromImage(img)
        self._render_scale = pixel_scale
        self._render_w = render_w
        self._render_h = render_h
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
        padding = 8
        w, h = self.width() - padding * 2, self.height() - padding * 2
        if self._doc_width <= 0 or self._doc_height <= 0:
            return QRectF(padding, padding, w, h), 1.0

        scale = min(w / self._doc_width, h / self._doc_height)
        pw = self._doc_width * scale
        ph = self._doc_height * scale
        ox = (self.width() - pw) / 2
        oy = (self.height() - ph) / 2
        return QRectF(ox, oy, pw, ph), scale

    def paintEvent(self, event):
        p = QPainter(self)
        # Piksel sanatı için nearest-neighbor — ASLA smooth kullanma
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Koyu arka plan
        p.fillRect(self.rect(), QColor(25, 25, 30))

        draw_rect, scale = self._get_draw_rect()

        if not self._preview.isNull():
            p.drawPixmap(draw_rect.toRect(), self._preview)

        # Viewport çerçevesi (kırmızı)
        if not self._viewport_rect.isNull() and self._doc_width > 0:
            vr = QRectF(
                draw_rect.x() + self._viewport_rect.x() * scale,
                draw_rect.y() + self._viewport_rect.y() * scale,
                self._viewport_rect.width() * scale,
                self._viewport_rect.height() * scale
            )
            pen = QPen(QColor(255, 60, 60, 220), 2)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(vr)

        p.end()

    def resizeEvent(self, event):
        """Widget boyutu değiştiğinde önizlemeyi yeniden oluştur."""
        super().resizeEvent(event)
        self.update_preview()

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
