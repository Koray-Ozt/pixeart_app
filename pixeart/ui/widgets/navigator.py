from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QPushButton, QFrame
from PyQt6.QtCore import Qt, QRectF, QPointF, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QImage, QPixmap, QPen, QMouseEvent, QBrush


class NavigatorPreview(QWidget):
    """
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
        
        self.setMinimumSize(180, 120)
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

        draw_rect, _ = self._get_draw_rect()
        target_w = max(int(draw_rect.width()), 1)
        target_h = max(int(draw_rect.height()), 1)

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
        c1, c2 = QColor("#3a3a3a"), QColor("#454545")
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
        padding = 12
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
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Koyu arka plan (derin kömür)
        p.fillRect(self.rect(), QColor(22, 22, 26))

        draw_rect, scale = self._get_draw_rect()

        if not self._preview.isNull():
            # Gölge efekti
            shadow_rect = draw_rect.translated(2, 2)
            p.fillRect(shadow_rect, QColor(0, 0, 0, 100))
            p.drawPixmap(draw_rect.toRect(), self._preview)
            
            # Kenarlık
            p.setPen(QPen(QColor(60, 60, 70), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(draw_rect)

        # Viewport çerçevesi (modern kırmızı)
        if not self._viewport_rect.isNull() and self._doc_width > 0:
            vr = QRectF(
                draw_rect.x() + self._viewport_rect.x() * scale,
                draw_rect.y() + self._viewport_rect.y() * scale,
                self._viewport_rect.width() * scale,
                self._viewport_rect.height() * scale
            )
            
            # Yarı saydam dolgu
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(255, 60, 60, 30)))
            p.drawRect(vr)
            
            # Çizgi kenarlık
            pen = QPen(QColor(255, 80, 80), 1.5)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(vr)

    def resizeEvent(self, event):
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


class NavigatorWidget(QWidget):
    """
    Modern Navigator (Gezgin) widget'ı.
    Önizleme alanı ve yakınlaştırma kontrollerini barındırır.
    """
    def __init__(self, canvas_view=None, canvas_scene=None, parent=None):
        super().__init__(parent)
        self._canvas_view = canvas_view
        self._canvas_scene = canvas_scene
        
        self._init_ui()
        self._apply_styling()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 1. Önizleme Alanı
        self.preview = NavigatorPreview(self._canvas_view, self._canvas_scene)
        layout.addWidget(self.preview, 1)
        
        # 2. Kontrol Çubuğu
        self.controls = QFrame()
        self.controls.setObjectName("navigatorControls")
        self.controls.setFixedHeight(42)  # Biraz daha yüksek
        controls_layout = QHBoxLayout(self.controls)
        controls_layout.setContentsMargins(10, 4, 10, 4)
        controls_layout.setSpacing(12)
        
        # Sığdır Butonu
        self.fit_btn = QPushButton("SIĞDIR")
        self.fit_btn.setToolTip("Görseli ekrana sığdır")
        self.fit_btn.setFixedWidth(54)
        self.fit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fit_btn.clicked.connect(self._on_fit_clicked)
        controls_layout.addWidget(self.fit_btn)
        
        # Zoom Slider
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 5000)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setCursor(Qt.CursorShape.SizeHorCursor)
        self.zoom_slider.valueChanged.connect(self._on_slider_changed)
        controls_layout.addWidget(self.zoom_slider)
        
        # Zoom Yüzde Etiketi
        self.zoom_label = QLabel("100%")
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.zoom_label.setFixedWidth(50)
        self.zoom_label.setObjectName("zoomLabel")
        self.zoom_label.setToolTip("Tıkla ve %100 yap")
        self.zoom_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zoom_label.mousePressEvent = lambda e: self._on_zoom_label_clicked()
        controls_layout.addWidget(self.zoom_label)
        
        layout.addWidget(self.controls)
        
        # Canvas sinyallerini bağla
        if self._canvas_view:
            self._canvas_view.zoom_changed.connect(self._update_zoom_ui)
            
    def _apply_styling(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1c;
                color: #e0e0e0;
                font-family: 'Inter', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                font-size: 11px;
            }
            #navigatorControls {
                background-color: #212123;
                border-top: 1px solid #2d2d30;
            }
            QPushButton {
                background-color: #323235;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 4px 6px;
                color: #dcdcdc;
                font-weight: bold;
                font-size: 10px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: #45454a;
                border-color: #505055;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #1e1e1f;
                border-color: #252526;
            }
            QSlider::groove:horizontal {
                border: none;
                height: 3px;
                background: #333336;
                margin: 2px 0;
                border-radius: 1.5px;
            }
            QSlider::handle:horizontal {
                background: #4a9eff;
                border: none;
                width: 10px;
                height: 10px;
                margin: -3.5px 0;
                border-radius: 5px;
            }
            QSlider::handle:horizontal:hover {
                background: #6ab0ff;
                box-shadow: 0 0 5px rgba(74, 158, 255, 0.5);
            }
            #zoomLabel {
                color: #b0b0b0;
                font-weight: 600;
                font-variant-numeric: tabular-nums;
            }
            #zoomLabel:hover {
                color: #4a9eff;
            }
        """)

    def set_canvas(self, canvas_view, canvas_scene):
        self._canvas_view = canvas_view
        self._canvas_scene = canvas_scene
        self.preview.set_canvas(canvas_view, canvas_scene)
        # Sinyalleri yeniden bağla
        try:
            self._canvas_view.zoom_changed.disconnect(self._update_zoom_ui)
        except:
            pass
        self._canvas_view.zoom_changed.connect(self._update_zoom_ui)

    def update_preview(self):
        self.preview.update_preview()

    def _on_fit_clicked(self):
        if self._canvas_view:
            self._canvas_view.reset_view()

    def _on_slider_changed(self, value):
        if self._canvas_view:
            # Canvas zoom'unu ayarla. Bu, zoom_changed sinyalini tetikleyecektir.
            self._canvas_view.set_zoom(value / 100.0)
            self.zoom_label.setText(f"{value}%")

    def _on_zoom_label_clicked(self):
        if self._canvas_view:
            self._canvas_view.set_zoom(1.0)

    def _update_zoom_ui(self, zoom_percentage):
        # Slider ve etiketi güncelle. 
        # Slider'ın valueChanged sinyalini engelliyoruz ki geri besleme döngüsü oluşmasın.
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(int(zoom_percentage))
        self.zoom_slider.blockSignals(False)
        self.zoom_label.setText(f"{int(zoom_percentage)}%")
        # Önizlemedeki kırmızı çerçeveyi de güncelle
        self.preview._update_viewport_rect()
