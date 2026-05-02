import math
import colorsys
import os
from typing import List, Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFrame, QSpinBox, QFileDialog, QScrollArea,
    QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize
from PyQt6.QtGui import (
    QColor, QPainter, QMouseEvent, QPen, QImage, QPixmap,
    QLinearGradient, QBrush, QAction
)
from pixeart.core.color import Color as CoreColor

DB16_COLORS = [
    "#140c1c", "#442434", "#30346d", "#4e4a4e",
    "#854c30", "#346524", "#d04648", "#757161",
    "#597dce", "#d27d2c", "#8595a1", "#6daa2c",
    "#d2aa99", "#6dc2ca", "#dad45e", "#deeed6"
]

MAX_RECENT = 12

# ---------------------------------------------------------------------------
# HSV Renk Seçici Bileşenleri
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
        if self._hue != h:
            self._hue = h
            self._cache = None
            self.update()

    def set_sv(self, s, v):
        if self._sat != s or self._val != v:
            self._sat = max(0, min(255, s))
            self._val = max(0, min(255, v))
            self.update()

    def _build_cache(self):
        sz = self.width()
        self._cache = QPixmap(sz, sz)
        p = QPainter(self._cache)
        base_color = QColor.fromHsv(self._hue, 255, 255)
        p.fillRect(0, 0, sz, sz, base_color)
        sat_grad = QLinearGradient(0, 0, sz, 0)
        sat_grad.setColorAt(0, Qt.GlobalColor.white)
        sat_grad.setColorAt(1, Qt.GlobalColor.transparent)
        p.fillRect(0, 0, sz, sz, QBrush(sat_grad))
        val_grad = QLinearGradient(0, 0, 0, sz)
        val_grad.setColorAt(0, Qt.GlobalColor.transparent)
        val_grad.setColorAt(1, Qt.GlobalColor.black)
        p.fillRect(0, 0, sz, sz, QBrush(val_grad))
        p.end()

    def paintEvent(self, event):
        if self._cache is None or self._cache.width() != self.width():
            self._build_cache()
        p = QPainter(self)
        p.drawPixmap(0, 0, self._cache)
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
# Renk Teorisi ve Ramp Bileşenleri
# ---------------------------------------------------------------------------
class MiniSwatch(QFrame):
    clicked = pyqtSignal(QColor)

    def __init__(self, color: QColor, size: int = 20):
        super().__init__()
        self.color = color
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(color.name().upper())
        self.update_style()

    def update_style(self):
        self.setStyleSheet(f"background-color: {self.color.name()}; border: 1px solid #333; border-radius: 2px;")

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.color)

class HarmonyWidget(QWidget):
    color_selected = pyqtSignal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)

    def update_harmonies(self, qcolor: QColor):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        core_color = CoreColor(qcolor.red(), qcolor.green(), qcolor.blue())
        harmonies = core_color.get_harmonies()
        
        for group, colors in harmonies.items():
            for c in colors:
                sw = MiniSwatch(QColor(c.r, c.g, c.b))
                sw.setToolTip(f"{group.capitalize()}: {sw.color.name().upper()}")
                sw.clicked.connect(self.color_selected)
                self.layout.addWidget(sw)
        self.layout.addStretch()

class RampWidget(QWidget):
    color_selected = pyqtSignal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)

    def update_ramp(self, qcolor: QColor):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        core_color = CoreColor(qcolor.red(), qcolor.green(), qcolor.blue())
        ramp = core_color.get_ramp(3, 3)
        
        for c in ramp:
            sw = MiniSwatch(QColor(c.r, c.g, c.b), 18)
            sw.clicked.connect(self.color_selected)
            self.layout.addWidget(sw)
        self.layout.addStretch()

# ---------------------------------------------------------------------------
# Ana Palet Yönetimi
# ---------------------------------------------------------------------------
class SwatchItem(QFrame):
    clicked = pyqtSignal(QColor, Qt.MouseButton)

    def __init__(self, color_hex: str, parent=None):
        super().__init__(parent)
        self.color = QColor(color_hex)
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(color_hex.upper())
        self.setStyleSheet(f"QFrame {{ background-color: {color_hex}; border: 1px solid #222; border-radius: 2px; }} QFrame:hover {{ border: 1px solid #fff; }}")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() in [Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton]:
            self.clicked.emit(self.color, event.button())

class CurrentColorsWidget(QWidget):
    primary_changed = pyqtSignal(QColor)
    secondary_changed = pyqtSignal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(64, 64)
        self.primary_color = QColor(DB16_COLORS[0])
        self.secondary_color = QColor(DB16_COLORS[15])

    def set_primary(self, color: QColor):
        if self.primary_color != color:
            self.primary_color = QColor(color)
            self.primary_changed.emit(self.primary_color)
            self.update()

    def set_secondary(self, color: QColor):
        if self.secondary_color != color:
            self.secondary_color = QColor(color)
            self.secondary_changed.emit(self.secondary_color)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(20, 20, 40, 40, self.secondary_color)
        painter.setPen(QPen(QColor("#111"), 1))
        painter.drawRect(20, 20, 39, 39)
        painter.fillRect(4, 4, 40, 40, self.primary_color)
        painter.setPen(QPen(QColor("#111"), 1))
        painter.drawRect(4, 4, 39, 39)

class RecentColorsWidget(QWidget):
    color_picked = pyqtSignal(QColor, Qt.MouseButton)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._colors = []
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(3)
        self._layout.addStretch()

    def add_color(self, color: QColor):
        hex_val = color.name()
        for c in self._colors:
            if c.name() == hex_val: return
        self._colors.insert(0, QColor(color))
        if len(self._colors) > MAX_RECENT: self._colors.pop()
        self._rebuild()

    def _rebuild(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
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

def _make_spin(label_text: str, max_val: int, value: int):
    lbl = QLabel(label_text)
    lbl.setStyleSheet("color:#aaa; font-size:11px;")
    spin = QSpinBox()
    spin.setRange(0, max_val)
    spin.setValue(value)
    spin.setStyleSheet("QSpinBox { background:#1e1e1e; color:white; border:1px solid #444; font-size:11px; } QSpinBox::up-button, QSpinBox::down-button { width:0px; }")
    return lbl, spin

class ColorPalette(QWidget):
    primary_color_changed = pyqtSignal(QColor)
    secondary_color_changed = pyqtSignal(QColor)
    extract_palette_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._suppress_sync = False
        self._current_palette = DB16_COLORS.copy()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 1. Colors & Swap
        top_row = QHBoxLayout()
        self.current_colors = CurrentColorsWidget()
        self.current_colors.primary_changed.connect(self._on_primary_changed_external)
        self.current_colors.secondary_changed.connect(self.secondary_color_changed)
        
        self.btn_swap = QPushButton("⇄")
        self.btn_swap.setFixedSize(32, 24)
        self.btn_swap.clicked.connect(self.swap_colors)
        self.btn_swap.setStyleSheet("QPushButton { background:#333; color:white; border:1px solid #444; border-radius:4px; }")
        
        top_row.addWidget(self.current_colors)
        top_row.addWidget(self.btn_swap)
        top_row.addStretch()
        layout.addLayout(top_row)

        # 2. Picker
        self._add_separator(layout, "Renk Seçici")
        self.sv_square = SVSquare()
        self.hue_bar = HueBar()
        self.sv_square.sv_changed.connect(self._on_sv_changed)
        self.hue_bar.hue_changed.connect(self._on_hue_changed)
        layout.addWidget(self.sv_square, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.hue_bar)

        # 3. Harmonies & Ramp
        v_theory = QVBoxLayout()
        self._add_separator(v_theory, "Uyumlar (Harmonies)")
        self.harmony_view = HarmonyWidget()
        self.harmony_view.color_selected.connect(self.current_colors.set_primary)
        v_theory.addWidget(self.harmony_view)
        
        self._add_separator(v_theory, "Rampa (Ramp)")
        self.ramp_view = RampWidget()
        self.ramp_view.color_selected.connect(self.current_colors.set_primary)
        v_theory.addWidget(self.ramp_view)
        layout.addLayout(v_theory)

        # 4. Spines
        spin_grid = QGridLayout()
        lbl_r, self.spin_r = _make_spin("R", 255, 0)
        lbl_g, self.spin_g = _make_spin("G", 255, 0)
        lbl_b, self.spin_b = _make_spin("B", 255, 0)
        lbl_h, self.spin_h = _make_spin("H", 359, 0)
        lbl_s, self.spin_s = _make_spin("S", 255, 0)
        lbl_v, self.spin_v = _make_spin("V", 255, 0)
        for i, (l, s) in enumerate([(lbl_r, self.spin_r), (lbl_g, self.spin_g), (lbl_b, self.spin_b),
                                    (lbl_h, self.spin_h), (lbl_s, self.spin_s), (lbl_v, self.spin_v)]):
            spin_grid.addWidget(l, i//3, (i%3)*2)
            spin_grid.addWidget(s, i//3, (i%3)*2+1)
        layout.addLayout(spin_grid)

        for sp in (self.spin_r, self.spin_g, self.spin_b): sp.valueChanged.connect(self._on_rgb_spin_changed)
        for sp in (self.spin_h, self.spin_s, self.spin_v): sp.valueChanged.connect(self._on_hsv_spin_changed)

        # 5. Palette
        self._add_separator(layout, "Palet İşlemleri")
        act_row = QHBoxLayout()
        self.btn_extract = QPushButton("Tuvalden Çıkar")
        self.btn_extract.clicked.connect(self.extract_palette_requested.emit)
        self.btn_sort = QPushButton("Sırala ▼")
        self.btn_sort.clicked.connect(self._show_sort_menu)
        for b in (self.btn_extract, self.btn_sort):
            b.setStyleSheet("QPushButton { background:#333; color:#ccc; border:1px solid #444; font-size:10px; padding:3px; }")
            act_row.addWidget(b)
        layout.addLayout(act_row)

        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(4)
        self._load_palette(self._current_palette)
        layout.addLayout(self.grid_layout)

        # 6. Load/Recent
        self._add_separator(layout, "Son Renkler")
        self.recent_colors = RecentColorsWidget()
        self.recent_colors.color_picked.connect(self._on_swatch_clicked)
        layout.addWidget(self.recent_colors)

        self.btn_load = QPushButton("İçe Aktar (GPL, PAL, IMG)...")
        self.btn_load.clicked.connect(self._on_load_palette)
        self.btn_load.setStyleSheet("QPushButton { background:#444; color:white; border:1px solid #555; padding:5px; }")
        layout.addWidget(self.btn_load)
        layout.addStretch()
        self._sync_ui_to_color(self.current_colors.primary_color)

    def _add_separator(self, layout, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color:#666; font-size:10px; font-weight:bold;")
        layout.addWidget(lbl)

    def _load_palette(self, hex_list):
        self._current_palette = hex_list
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for i, h in enumerate(hex_list):
            sw = SwatchItem(h)
            sw.clicked.connect(self._on_swatch_clicked)
            self.grid_layout.addWidget(sw, i // 4, i % 4)

    def set_palette(self, hex_list):
        self._load_palette(list(set(hex_list)))

    def _show_sort_menu(self):
        menu = QMenu(self)
        a_hue = menu.addAction("Ton (Hue)")
        a_sat = menu.addAction("Doygunluk (Saturation)")
        a_lum = menu.addAction("Parlaklık (Luminance)")
        act = menu.exec(self.btn_sort.mapToGlobal(QPoint(0, self.btn_sort.height())))
        if not act: return
        
        colors = [CoreColor.from_hex(h) for h in self._current_palette]
        if act == a_hue: colors.sort(key=lambda c: c.to_hsv()[0])
        elif act == a_sat: colors.sort(key=lambda c: c.to_hsv()[1])
        elif act == a_lum: colors.sort(key=lambda c: c.luminance)
        self._load_palette([c.to_hex() for c in colors])

    def _sync_ui_to_color(self, color: QColor):
        """Bileşenleri (Picker, Spins, Harmonies) verilen renge göre günceller."""
        self._suppress_sync = True
        try:
            h, s, v, _ = color.getHsv()
            if h < 0: h = 0
            
            # Picker
            self.hue_bar.hue = h
            self.sv_square.set_hue(h)
            self.sv_square.set_sv(s, v)
            
            # Spins
            self.spin_r.setValue(color.red())
            self.spin_g.setValue(color.green())
            self.spin_b.setValue(color.blue())
            self.spin_h.setValue(h)
            self.spin_s.setValue(s)
            self.spin_v.setValue(v)
            
            # Theory
            self.harmony_view.update_harmonies(color)
            self.ramp_view.update_ramp(color)
        finally:
            self._suppress_sync = False

    def _on_hue_changed(self, h):
        if self._suppress_sync: return
        self._apply_current_picker_color()

    def _on_sv_changed(self, s, v):
        if self._suppress_sync: return
        self._apply_current_picker_color()

    def _apply_current_picker_color(self):
        """Picker'daki değerleri ana renk yapar ve diğer UI elemanlarını günceller."""
        c = QColor.fromHsv(self.hue_bar.hue, self.sv_square._sat, self.sv_square._val)
        self._suppress_sync = True
        try:
            # Spins
            self.spin_r.setValue(c.red())
            self.spin_g.setValue(c.green())
            self.spin_b.setValue(c.blue())
            self.spin_h.setValue(self.hue_bar.hue)
            self.spin_s.setValue(self.sv_square._sat)
            self.spin_v.setValue(self.sv_square._val)
            
            # Main Color Box
            self.current_colors.set_primary(c)
            self.recent_colors.add_color(c)
            
            # Theory
            self.harmony_view.update_harmonies(c)
            self.ramp_view.update_ramp(c)
            
            # Notify rest of the app
            self.primary_color_changed.emit(c)
        finally:
            self._suppress_sync = False

    def _on_rgb_spin_changed(self):
        if self._suppress_sync: return
        c = QColor(self.spin_r.value(), self.spin_g.value(), self.spin_b.value())
        self._sync_ui_to_color(c)
        self.current_colors.set_primary(c)
        self.recent_colors.add_color(c)
        self.primary_color_changed.emit(c)

    def _on_hsv_spin_changed(self):
        if self._suppress_sync: return
        c = QColor.fromHsv(self.spin_h.value(), self.spin_s.value(), self.spin_v.value())
        self._sync_ui_to_color(c)
        self.current_colors.set_primary(c)
        self.recent_colors.add_color(c)
        self.primary_color_changed.emit(c)

    def _on_primary_changed_external(self, color: QColor):
        """CurrentColorsWidget'dan gelen (swap, swatch click vb) değişiklikleri karşılar."""
        if self._suppress_sync: return
        self._sync_ui_to_color(color)
        self.recent_colors.add_color(color)
        self.primary_color_changed.emit(color)

    def _on_swatch_clicked(self, color: QColor, button: Qt.MouseButton = Qt.MouseButton.LeftButton):
        if button == Qt.MouseButton.LeftButton:
            self.current_colors.set_primary(color)
        else:
            self.current_colors.set_secondary(color)

    def swap_colors(self):
        p, s = self.current_colors.primary_color, self.current_colors.secondary_color
        # Swap'ta sync geçici olarak durdurulur
        self._suppress_sync = True
        try:
            self.current_colors.set_primary(s)
            self.current_colors.set_secondary(p)
        finally:
            self._suppress_sync = False
        self._on_primary_changed_external(s)

    def _on_load_palette(self):
        path, _ = QFileDialog.getOpenFileName(self, "Palet / Görsel Seç", "", "Desteklenenler (*.gpl *.pal *.png *.jpg *.bmp);;Tüm Dosyalar (*)")
        if not path: return
        ext = os.path.splitext(path)[1].lower()
        if ext == ".gpl": colors = self._parse_gpl(path)
        elif ext == ".pal": colors = self._parse_pal(path)
        else: colors = self._parse_image(path)
        if colors: self._load_palette(colors)

    def _parse_gpl(self, path):
        colors = []
        try:
            with open(path, "r") as f:
                for line in f:
                    if line.startswith(("GIMP", "#", "Name", "Columns")): continue
                    p = line.split()
                    if len(p) >= 3: colors.append(QColor(int(p[0]), int(p[1]), int(p[2])).name())
        except: pass
        return colors

    def _parse_pal(self, path):
        colors = []
        try:
            with open(path, "r") as f:
                lines = f.readlines()
                if len(lines) > 3 and "JASC-PAL" in lines[0]:
                    for line in lines[3:]:
                        p = line.split()
                        if len(p) >= 3: colors.append(QColor(int(p[0]), int(p[1]), int(p[2])).name())
        except: pass
        return colors

    def _parse_image(self, path):
        img = QImage(path)
        if img.isNull(): return []
        colors = set()
        w, h = min(img.width(), 256), min(img.height(), 256)
        for y in range(h):
            for x in range(w):
                c = img.pixelColor(x, y)
                if c.alpha() > 0: colors.add(c.name())
                if len(colors) > 256: break
            if len(colors) > 256: break
        return list(colors)

    def get_primary_color(self) -> QColor: return self.current_colors.primary_color
    def get_secondary_color(self) -> QColor: return self.current_colors.secondary_color
