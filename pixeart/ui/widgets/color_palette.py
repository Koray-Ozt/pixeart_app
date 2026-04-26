import math
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFrame, QSpinBox, QFileDialog, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize
from PyQt6.QtGui import (
    QColor, QPainter, QMouseEvent, QPen, QImage, QPixmap,
    QLinearGradient, QConicalGradient, QRadialGradient, QBrush
)

DB16_COLORS = [
    "#140c1c", "#442434", "#30346d", "#4e4a4e",
    "#854c30", "#346524", "#d04648", "#757161",
    "#597dce", "#d27d2c", "#8595a1", "#6daa2c",
    "#d2aa99", "#6dc2ca", "#dad45e", "#deeed6"
]

MAX_RECENT = 12


# ---------------------------------------------------------------------------
# HSV Renk Karesi: Üstte Hue çubuğu, altında SV karesi
# ---------------------------------------------------------------------------
class HueBar(QWidget):
    hue_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(16)
        self.setMinimumWidth(100)
        self._hue = 0
        self._pressed = False
        self.setCursor(Qt.CursorShape.CrossCursor)

    @property
    def hue(self):
        return self._hue

    @hue.setter
    def hue(self, value):
        value = max(0, min(359, value))
        if self._hue != value:
            self._hue = value
            self.update()
            self.hue_changed.emit(self._hue)

    def paintEvent(self, event):
        p = QPainter(self)
        w, h = self.width(), self.height()
        for x in range(w):
            ratio = x / max(w - 1, 1)
            c = QColor.fromHsvF(ratio, 1.0, 1.0)
            p.setPen(c)
            p.drawLine(x, 0, x, h)
        # Marker
        mx = int(self._hue / 359 * (w - 1))
        p.setPen(QPen(QColor(255, 255, 255), 2))
        p.drawRect(mx - 2, 0, 4, h - 1)
        p.end()

    def _pick(self, pos):
        ratio = max(0.0, min(1.0, pos.x() / max(self.width() - 1, 1)))
        self.hue = int(ratio * 359)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self._pick(e.position().toPoint())

    def mouseMoveEvent(self, e):
        if self._pressed:
            self._pick(e.position().toPoint())

    def mouseReleaseEvent(self, e):
        self._pressed = False


class SVSquare(QWidget):
    sv_changed = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 160)
        self._hue = 0
        self._sat = 255
        self._val = 255
        self._pressed = False
        self._cache = None
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_hue(self, h):
        self._hue = h
        self._cache = None
        self.update()

    def set_sv(self, s, v):
        self._sat = max(0, min(255, s))
        self._val = max(0, min(255, v))
        self.update()

    def _build_cache(self):
        sz = self.width()
        img = QImage(sz, sz, QImage.Format.Format_RGB32)
        for y in range(sz):
            val = 1.0 - y / max(sz - 1, 1)
            for x in range(sz):
                sat = x / max(sz - 1, 1)
                c = QColor.fromHsvF(self._hue / 360.0, sat, val)
                img.setPixelColor(x, y, c)
        self._cache = QPixmap.fromImage(img)

    def paintEvent(self, event):
        if self._cache is None or self._cache.width() != self.width():
            self._build_cache()
        p = QPainter(self)
        p.drawPixmap(0, 0, self._cache)
        # Marker
        sz = self.width()
        mx = int(self._sat / 255 * (sz - 1))
        my = int((1.0 - self._val / 255) * (sz - 1))
        p.setPen(QPen(Qt.GlobalColor.white, 2))
        p.drawEllipse(QPoint(mx, my), 5, 5)
        p.setPen(QPen(Qt.GlobalColor.black, 1))
        p.drawEllipse(QPoint(mx, my), 6, 6)
        p.end()

    def _pick(self, pos):
        sz = self.width()
        x = max(0, min(sz - 1, pos.x()))
        y = max(0, min(sz - 1, pos.y()))
        self._sat = int(x / max(sz - 1, 1) * 255)
        self._val = int((1.0 - y / max(sz - 1, 1)) * 255)
        self.update()
        self.sv_changed.emit(self._sat, self._val)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self._pick(e.position().toPoint())

    def mouseMoveEvent(self, e):
        if self._pressed:
            self._pick(e.position().toPoint())

    def mouseReleaseEvent(self, e):
        self._pressed = False


# ---------------------------------------------------------------------------
# Swatch (Palet karesi)
# ---------------------------------------------------------------------------
class SwatchItem(QFrame):
    clicked = pyqtSignal(QColor, Qt.MouseButton)

    def __init__(self, color_hex: str, parent=None):
        super().__init__(parent)
        self.color = QColor(color_hex)
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(color_hex.upper())
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {color_hex};
                border: 1px solid #222;
                border-radius: 2px;
            }}
            QFrame:hover {{
                border: 1px solid #fff;
            }}
        """)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() in [Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton]:
            self.clicked.emit(self.color, event.button())
            event.accept()
        else:
            super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# Birincil / İkincil Renk Kutusu (Büyük önizleme)
# ---------------------------------------------------------------------------
class CurrentColorsWidget(QWidget):
    primary_changed = pyqtSignal(QColor)
    secondary_changed = pyqtSignal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(64, 64)
        self.primary_color = QColor(DB16_COLORS[0])
        self.secondary_color = QColor(DB16_COLORS[15])
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_primary(self, color: QColor):
        self.primary_color = QColor(color)
        self.primary_changed.emit(self.primary_color)
        self.update()

    def set_secondary(self, color: QColor):
        self.secondary_color = QColor(color)
        self.secondary_changed.emit(self.secondary_color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(20, 20, 40, 40, self.secondary_color)
        painter.setPen(QPen(QColor("#111"), 1))
        painter.drawRect(20, 20, 39, 39)
        painter.fillRect(4, 4, 40, 40, self.primary_color)
        painter.setPen(QPen(QColor("#111"), 1))
        painter.drawRect(4, 4, 39, 39)
        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        event.accept()


# ---------------------------------------------------------------------------
# Son Renkler (Recent Colors) Bölümü
# ---------------------------------------------------------------------------
class RecentColorsWidget(QWidget):
    color_picked = pyqtSignal(QColor, Qt.MouseButton)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._colors = []
        self._init_ui()

    def _init_ui(self):
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(3)
        self._layout.addStretch()

    def add_color(self, color: QColor):
        hex_val = color.name()
        for c in self._colors:
            if c.name() == hex_val:
                return
        self._colors.insert(0, QColor(color))
        if len(self._colors) > MAX_RECENT:
            self._colors.pop()
        self._rebuild()

    def _rebuild(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        for c in self._colors:
            frame = QFrame()
            frame.setFixedSize(20, 20)
            frame.setCursor(Qt.CursorShape.PointingHandCursor)
            frame.setStyleSheet(f"background-color: {c.name()}; border: 1px solid #333; border-radius: 2px;")
            frame.mousePressEvent = lambda e, col=c: self._on_click(e, col)
            self._layout.addWidget(frame)
        self._layout.addStretch()

    def _on_click(self, event, color):
        if event.button() in [Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton]:
            self.color_picked.emit(color, event.button())


# ---------------------------------------------------------------------------
# Küçük etiketli SpinBox satırı üreteci
# ---------------------------------------------------------------------------
def _make_spin(label_text: str, max_val: int, value: int):
    lbl = QLabel(label_text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet("color:#aaa; font-size:11px; font-weight:bold;")
    spin = QSpinBox()
    spin.setRange(0, max_val)
    spin.setValue(value)
    spin.setStyleSheet("""
        QSpinBox { background:#1e1e1e; color:white; border:1px solid #444; border-radius:2px; padding:1px; font-size:11px; }
        QSpinBox:focus { border:1px solid #007acc; }
        QSpinBox::up-button, QSpinBox::down-button { width:0px; }
    """)
    return lbl, spin


# ---------------------------------------------------------------------------
# Ana Renk Paleti Widget'ı
# ---------------------------------------------------------------------------
class ColorPalette(QWidget):
    primary_color_changed = pyqtSignal(QColor)
    secondary_color_changed = pyqtSignal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._suppress_spin_update = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # === 1. Birincil/İkincil Renk Kutusu + Swap ===
        top_layout = QHBoxLayout()
        self.current_colors = CurrentColorsWidget()
        self.current_colors.primary_changed.connect(self._on_primary_changed_external)
        self.current_colors.secondary_changed.connect(self.secondary_color_changed)

        self.btn_swap = QPushButton("⇄")
        self.btn_swap.setFixedSize(32, 24)
        self.btn_swap.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_swap.setToolTip("Renkleri Değiştir (X)")
        self.btn_swap.setStyleSheet("QPushButton { background:#333; color:white; border-radius:4px; border:1px solid #444; font-size:14px;} QPushButton:hover { background:#444; }")
        self.btn_swap.clicked.connect(self.swap_colors)

        top_layout.addWidget(self.current_colors)
        swap_col = QVBoxLayout()
        swap_col.addWidget(self.btn_swap)
        swap_col.addStretch()
        top_layout.addLayout(swap_col)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # === 2. HSV Renk Seçici ===
        self._add_separator(layout, "Renk Seçici")

        self.hue_bar = HueBar()
        self.sv_square = SVSquare()
        self.hue_bar.hue_changed.connect(self._on_hue_changed)
        self.sv_square.sv_changed.connect(self._on_sv_changed)
        layout.addWidget(self.sv_square, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.hue_bar)

        # === 3. RGB / HSV SpinBox'lar ===
        spin_grid = QGridLayout()
        spin_grid.setSpacing(4)

        lbl_r, self.spin_r = _make_spin("R", 255, 0)
        lbl_g, self.spin_g = _make_spin("G", 255, 0)
        lbl_b, self.spin_b = _make_spin("B", 255, 0)
        lbl_h, self.spin_h = _make_spin("H", 359, 0)
        lbl_s, self.spin_s = _make_spin("S", 255, 0)
        lbl_v, self.spin_v = _make_spin("V", 255, 0)

        spin_grid.addWidget(lbl_r, 0, 0); spin_grid.addWidget(self.spin_r, 0, 1)
        spin_grid.addWidget(lbl_g, 0, 2); spin_grid.addWidget(self.spin_g, 0, 3)
        spin_grid.addWidget(lbl_b, 0, 4); spin_grid.addWidget(self.spin_b, 0, 5)
        spin_grid.addWidget(lbl_h, 1, 0); spin_grid.addWidget(self.spin_h, 1, 1)
        spin_grid.addWidget(lbl_s, 1, 2); spin_grid.addWidget(self.spin_s, 1, 3)
        spin_grid.addWidget(lbl_v, 1, 4); spin_grid.addWidget(self.spin_v, 1, 5)
        layout.addLayout(spin_grid)

        for sp in (self.spin_r, self.spin_g, self.spin_b):
            sp.valueChanged.connect(self._on_rgb_spin_changed)
        for sp in (self.spin_h, self.spin_s, self.spin_v):
            sp.valueChanged.connect(self._on_hsv_spin_changed)

        # === 4. Son Renkler ===
        self._add_separator(layout, "Son Renkler")
        self.recent_colors = RecentColorsWidget()
        self.recent_colors.color_picked.connect(self._on_swatch_clicked)
        layout.addWidget(self.recent_colors)

        # === 5. Sabit Palet (DB16) ===
        self._add_separator(layout, "Palet")
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(4)
        self._load_palette(DB16_COLORS)
        layout.addLayout(self.grid_layout)

        # === 6. Palet Yükle Butonu (.gpl) ===
        self.btn_load_palette = QPushButton("Palet Yükle (.gpl)")
        self.btn_load_palette.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load_palette.setStyleSheet("""
            QPushButton { background:#333; color:#ccc; border:1px solid #444; border-radius:4px; padding:5px; font-size:11px; }
            QPushButton:hover { background:#444; color:white; border:1px solid #666; }
        """)
        self.btn_load_palette.clicked.connect(self._on_load_palette)
        layout.addWidget(self.btn_load_palette)

        layout.addStretch()

        # İlk renk senkronizasyonu
        self._sync_picker_to_color(self.current_colors.primary_color)

    # -----------------------------------------------------------------------
    # Yardımcılar
    # -----------------------------------------------------------------------
    @staticmethod
    def _add_separator(layout, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color:#888; font-size:11px;")
        layout.addWidget(lbl)

    def _load_palette(self, hex_list):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        for i, hex_color in enumerate(hex_list):
            row, col = divmod(i, 4)
            swatch = SwatchItem(hex_color)
            swatch.clicked.connect(self._on_swatch_clicked)
            self.grid_layout.addWidget(swatch, row, col)

    # -----------------------------------------------------------------------
    # Renk seçici <-> SpinBox <-> CurrentColors senkronizasyonu
    # -----------------------------------------------------------------------
    def _sync_picker_to_color(self, color: QColor):
        self._suppress_spin_update = True
        h, s, v, _ = color.getHsv()
        if h < 0:
            h = 0
        self.hue_bar.hue = h
        self.sv_square.set_hue(h)
        self.sv_square.set_sv(s, v)
        self.spin_r.setValue(color.red())
        self.spin_g.setValue(color.green())
        self.spin_b.setValue(color.blue())
        self.spin_h.setValue(h)
        self.spin_s.setValue(s)
        self.spin_v.setValue(v)
        self._suppress_spin_update = False

    def _apply_current_hsv(self):
        c = QColor.fromHsv(self.hue_bar.hue, self.sv_square._sat, self.sv_square._val)
        self._suppress_spin_update = True
        self.spin_r.setValue(c.red())
        self.spin_g.setValue(c.green())
        self.spin_b.setValue(c.blue())
        self.spin_h.setValue(self.hue_bar.hue)
        self.spin_s.setValue(self.sv_square._sat)
        self.spin_v.setValue(self.sv_square._val)
        self._suppress_spin_update = False
        self.current_colors.set_primary(c)
        self.recent_colors.add_color(c)

    def _on_hue_changed(self, h):
        self.sv_square.set_hue(h)
        self._apply_current_hsv()

    def _on_sv_changed(self, s, v):
        self._apply_current_hsv()

    def _on_rgb_spin_changed(self):
        if self._suppress_spin_update:
            return
        c = QColor(self.spin_r.value(), self.spin_g.value(), self.spin_b.value())
        self._suppress_spin_update = True
        h, s, v, _ = c.getHsv()
        if h < 0:
            h = 0
        self.hue_bar.hue = h
        self.sv_square.set_hue(h)
        self.sv_square.set_sv(s, v)
        self.spin_h.setValue(h)
        self.spin_s.setValue(s)
        self.spin_v.setValue(v)
        self._suppress_spin_update = False
        self.current_colors.set_primary(c)
        self.recent_colors.add_color(c)

    def _on_hsv_spin_changed(self):
        if self._suppress_spin_update:
            return
        h = self.spin_h.value()
        s = self.spin_s.value()
        v = self.spin_v.value()
        c = QColor.fromHsv(h, s, v)
        self._suppress_spin_update = True
        self.hue_bar.hue = h
        self.sv_square.set_hue(h)
        self.sv_square.set_sv(s, v)
        self.spin_r.setValue(c.red())
        self.spin_g.setValue(c.green())
        self.spin_b.setValue(c.blue())
        self._suppress_spin_update = False
        self.current_colors.set_primary(c)
        self.recent_colors.add_color(c)

    # -----------------------------------------------------------------------
    # Harici renk seçimleri (swatch, picker tool, vb.)
    # -----------------------------------------------------------------------
    def _on_primary_changed_external(self, color: QColor):
        self._sync_picker_to_color(color)
        self.recent_colors.add_color(color)
        self.primary_color_changed.emit(color)

    def _on_swatch_clicked(self, color: QColor, button: Qt.MouseButton):
        if button == Qt.MouseButton.LeftButton:
            self.current_colors.set_primary(color)
        elif button == Qt.MouseButton.RightButton:
            self.current_colors.set_secondary(color)

    def swap_colors(self):
        p = QColor(self.current_colors.primary_color)
        s = QColor(self.current_colors.secondary_color)
        self.current_colors.set_primary(s)
        self.current_colors.set_secondary(p)

    # -----------------------------------------------------------------------
    # .gpl Palet Yükleme
    # -----------------------------------------------------------------------
    def _on_load_palette(self):
        path, _ = QFileDialog.getOpenFileName(self, "Palet Dosyası Aç", "", "GIMP Palette (*.gpl);;Tüm Dosyalar (*)")
        if not path:
            return
        colors = self._parse_gpl(path)
        if colors:
            self._load_palette(colors)

    @staticmethod
    def _parse_gpl(file_path: str):
        colors = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("GIMP") or line.startswith("Name") or line.startswith("Columns"):
                        continue
                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                            colors.append(QColor(r, g, b).name())
                        except ValueError:
                            continue
        except OSError:
            return []
        return colors

    # -----------------------------------------------------------------------
    # Genel API (main_window & tool_manager uyumluluğu)
    # -----------------------------------------------------------------------
    def get_primary_color(self) -> QColor:
        return self.current_colors.primary_color

    def get_secondary_color(self) -> QColor:
        return self.current_colors.secondary_color
