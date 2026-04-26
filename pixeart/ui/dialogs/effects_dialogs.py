from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSlider, QCheckBox, QColorDialog,
    QSpinBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

class BaseEffectDialog(QDialog):
    preview_requested = pyqtSignal(bool, dict) # (preview_is_active, args_dict)
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(300)
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: white; }
            QLabel { color: #e0e0e0; }
            QSlider::groove:horizontal { border: 1px solid #999; height: 8px; background: #333; margin: 2px 0; border-radius: 4px; }
            QSlider::handle:horizontal { background: #55aaff; border: 1px solid #5c5c5c; width: 14px; margin: -4px 0; border-radius: 7px; }
            QPushButton { background-color: #3d3d3d; color: white; border: 1px solid #555; padding: 6px; border-radius: 4px; }
            QPushButton:hover { background-color: #4d4d4d; }
            QPushButton:pressed { background-color: #005a9e; }
        """)
        
        self.layout = QVBoxLayout(self)
        self._build_ui()
        
        # Preview ve Dialog butonları
        self.preview_cb = QCheckBox("Önizleme (Preview)")
        self.preview_cb.setChecked(True)
        self.preview_cb.stateChanged.connect(self._emit_preview)
        
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Tamam")
        self.btn_cancel = QPushButton("İptal")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.preview_cb)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        
        self.layout.addLayout(btn_layout)

    def _build_ui(self):
        pass # Alt sınıflar dolduracak
        
    def _get_args(self) -> dict:
        return {}
        
    def _emit_preview(self):
        self.preview_requested.emit(self.preview_cb.isChecked(), self._get_args())


class BrightnessContrastDialog(BaseEffectDialog):
    def __init__(self, parent=None):
        super().__init__("Parlaklık ve Kontrast", parent)
        
    def _build_ui(self):
        # Brightness
        b_layout = QHBoxLayout()
        b_layout.addWidget(QLabel("Parlaklık:"))
        self.b_slider = QSlider(Qt.Orientation.Horizontal)
        self.b_slider.setRange(-100, 100)
        self.b_slider.setValue(0)
        self.b_val = QLabel("0")
        b_layout.addWidget(self.b_slider)
        b_layout.addWidget(self.b_val)
        self.layout.addLayout(b_layout)
        
        # Contrast
        c_layout = QHBoxLayout()
        c_layout.addWidget(QLabel("Kontrast:"))
        self.c_slider = QSlider(Qt.Orientation.Horizontal)
        self.c_slider.setRange(-100, 100)
        self.c_slider.setValue(0)
        self.c_val = QLabel("0")
        c_layout.addWidget(self.c_slider)
        c_layout.addWidget(self.c_val)
        self.layout.addLayout(c_layout)
        
        self.b_slider.valueChanged.connect(self._on_b_change)
        self.c_slider.valueChanged.connect(self._on_c_change)
        
    def _on_b_change(self, val):
        self.b_val.setText(str(val))
        self._emit_preview()
        
    def _on_c_change(self, val):
        self.c_val.setText(str(val))
        self._emit_preview()
        
    def _get_args(self):
        return {"brightness": self.b_slider.value(), "contrast": self.c_slider.value()}


class HueSaturationDialog(BaseEffectDialog):
    def __init__(self, parent=None):
        super().__init__("Ton ve Doygunluk (Hue/Sat)", parent)
        
    def _build_ui(self):
        def make_slider(name, min_val, max_val):
            l = QHBoxLayout()
            l.addWidget(QLabel(name))
            s = QSlider(Qt.Orientation.Horizontal)
            s.setRange(min_val, max_val)
            s.setValue(0)
            v = QLabel("0")
            l.addWidget(s)
            l.addWidget(v)
            self.layout.addLayout(l)
            return s, v
            
        self.h_slider, self.h_val = make_slider("Ton (Hue):", -180, 180)
        self.s_slider, self.s_val = make_slider("Doygunluk:", -100, 100)
        self.l_slider, self.l_val = make_slider("Aydınlık:", -100, 100)
        
        for s, v in [(self.h_slider, self.h_val), (self.s_slider, self.s_val), (self.l_slider, self.l_val)]:
            s.valueChanged.connect(lambda val, lbl=v: lbl.setText(str(val)))
            s.valueChanged.connect(self._emit_preview)

    def _get_args(self):
        return {
            "hue_shift": self.h_slider.value(), 
            "sat_shift": self.s_slider.value(),
            "lightness_shift": self.l_slider.value()
        }


class ReplaceColorDialog(BaseEffectDialog):
    def __init__(self, target_color: QColor, parent=None):
        self.target_color = target_color
        self.new_color = QColor(target_color)
        super().__init__("Rengi Değiştir (Replace Color)", parent)
        
    def _build_ui(self):
        # Target Color
        t_layout = QHBoxLayout()
        t_layout.addWidget(QLabel("Hedef Renk:"))
        self.btn_target = QPushButton()
        self._update_btn_color(self.btn_target, self.target_color)
        self.btn_target.clicked.connect(self._pick_target)
        
        self.btn_eye = QPushButton("🎨 (Pick)")
        self.btn_eye.setToolTip("Tuvalden seç")
        self.btn_eye.clicked.connect(self._request_eye_drop)
        
        t_layout.addWidget(self.btn_target)
        t_layout.addWidget(self.btn_eye)
        self.layout.addLayout(t_layout)
        
        # New Color
        n_layout = QHBoxLayout()
        n_layout.addWidget(QLabel("Yeni Renk:"))
        self.btn_new = QPushButton()
        self._update_btn_color(self.btn_new, self.new_color)
        self.btn_new.clicked.connect(self._pick_new)
        n_layout.addWidget(self.btn_new)
        self.layout.addLayout(n_layout)
        
        # Tolerance
        tol_layout = QHBoxLayout()
        tol_layout.addWidget(QLabel("Tolerans:"))
        self.spin_tol = QSpinBox()
        self.spin_tol.setRange(0, 255)
        self.spin_tol.setValue(0)
        self.spin_tol.valueChanged.connect(self._emit_preview)
        tol_layout.addWidget(self.spin_tol)
        self.layout.addLayout(tol_layout)
        
    def _update_btn_color(self, btn, color):
        btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #fff; min-height: 24px;")
        
    def _request_eye_drop(self):
        # We temporarily hide the dialog, let main window handle a click, then return
        self.hide()
        p = self.parent()
        if p and hasattr(p, 'start_eyedropper_for_dialog'):
            p.start_eyedropper_for_dialog(self)
            
    def set_target_color(self, c: QColor):
        if c.isValid():
            self.target_color = c
            self._update_btn_color(self.btn_target, c)
            self.show()
            self._emit_preview()
        
    def _pick_target(self):
        c = QColorDialog.getColor(self.target_color, self, "Hedef Rengi Seç")
        if c.isValid():
            self.target_color = c
            self._update_btn_color(self.btn_target, c)
            self._emit_preview()
            
    def _pick_new(self):
        c = QColorDialog.getColor(self.new_color, self, "Yeni Rengi Seç")
        if c.isValid():
            self.new_color = c
            self._update_btn_color(self.btn_new, c)
            self._emit_preview()

    def _get_args(self):
        from pixeart.core.color import Color
        return {
            "target": Color(self.target_color.red(), self.target_color.green(), self.target_color.blue(), self.target_color.alpha()),
            "new_color": Color(self.new_color.red(), self.new_color.green(), self.new_color.blue(), self.new_color.alpha()),
            "tolerance": self.spin_tol.value()
        }


class OutlineDialog(BaseEffectDialog):
    def __init__(self, parent=None):
        self.outline_color = QColor(0, 0, 0, 255)
        super().__init__("Dış Çizgi (Outline)", parent)
        
    def _build_ui(self):
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Çizgi Rengi:"))
        self.btn_color = QPushButton()
        self.btn_color.setStyleSheet(f"background-color: {self.outline_color.name()}; min-height: 24px;")
        self.btn_color.clicked.connect(self._pick_color)
        layout.addWidget(self.btn_color)
        self.layout.addLayout(layout)
        
    def _pick_color(self):
        c = QColorDialog.getColor(self.outline_color, self, "Dış Çizgi Rengi")
        if c.isValid():
            self.outline_color = c
            self.btn_color.setStyleSheet(f"background-color: {c.name()}; min-height: 24px;")
            self._emit_preview()
            
    def _get_args(self):
        from pixeart.core.color import Color
        return {
            "outline_color": Color(self.outline_color.red(), self.outline_color.green(), self.outline_color.blue(), self.outline_color.alpha())
        }


class ConvolutionDialog(BaseEffectDialog):
    def __init__(self, parent=None):
        super().__init__("Matris Filtresi (Convolution)", parent)
        
    def _build_ui(self):
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Hazır Filtreler:"))
        self.combo = QComboBox()
        self.combo.addItems(["Bulanıklaştır (Blur)", "Keskinleştir (Sharpen)", "Kenar Bul (Edge Detect)"])
        self.combo.currentIndexChanged.connect(self._emit_preview)
        layout.addWidget(self.combo)
        self.layout.addLayout(layout)
        
    def _get_args(self):
        idx = self.combo.currentIndex()
        if idx == 0: # Blur
            matrix = [[1/9, 1/9, 1/9], [1/9, 1/9, 1/9], [1/9, 1/9, 1/9]]
        elif idx == 1: # Sharpen
            matrix = [[0, -1, 0], [-1, 5, -1], [0, -1, 0]]
        else: # Edge Detect
            matrix = [[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]]
            
        return {"matrix": matrix}


from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QPainterPath
from PyQt6.QtCore import QPointF

class CurveGraphWidget(QWidget):
    curve_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(256, 256)
        self.points = [QPointF(0.0, 0.0), QPointF(1.0, 1.0)]
        self.active_point_idx = -1
        
    def _to_rect_coords(self, p: QPointF) -> QPointF:
        return QPointF(p.x() * self.width(), (1.0 - p.y()) * self.height())
        
    def _to_norm_coords(self, p: QPointF) -> QPointF:
        x = max(0.0, min(1.0, p.x() / self.width()))
        y = max(0.0, min(1.0, 1.0 - (p.y() / self.height())))
        return QPointF(x, y)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.fillRect(self.rect(), QColor(30, 30, 30))
        painter.setPen(QPen(QColor(80, 80, 80), 1, Qt.PenStyle.DotLine))
        for i in range(1, 4):
            x = int(self.width() * i / 4)
            y = int(self.height() * i / 4)
            painter.drawLine(x, 0, x, self.height())
            painter.drawLine(0, y, self.width(), y)
            
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        path = QPainterPath()
        if self.points:
            p0 = self._to_rect_coords(self.points[0])
            path.moveTo(p0)
            for pt in self.points[1:]:
                path.lineTo(self._to_rect_coords(pt))
        painter.drawPath(path)
        
        for i, pt in enumerate(self.points):
            rect_pt = self._to_rect_coords(pt)
            painter.setBrush(QColor(255, 0, 0) if i == self.active_point_idx else QColor(255, 255, 255))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(rect_pt, 4, 4)

    def mousePressEvent(self, event):
        norm_pos = self._to_norm_coords(event.position())
        for i, pt in enumerate(self.points):
            if abs(pt.x() - norm_pos.x()) < 0.05 and abs(pt.y() - norm_pos.y()) < 0.05:
                self.active_point_idx = i
                self.update()
                return
                
        self.points.append(norm_pos)
        self.points.sort(key=lambda p: p.x())
        self.active_point_idx = self.points.index(norm_pos)
        self.update()
        self.curve_changed.emit()

    def mouseMoveEvent(self, event):
        if self.active_point_idx >= 0:
            norm_pos = self._to_norm_coords(event.position())
            
            min_x = self.points[self.active_point_idx - 1].x() + 0.01 if self.active_point_idx > 0 else 0.0
            max_x = self.points[self.active_point_idx + 1].x() - 0.01 if self.active_point_idx < len(self.points) - 1 else 1.0
            
            if self.active_point_idx == 0:
                norm_pos.setX(0.0)
            elif self.active_point_idx == len(self.points) - 1:
                norm_pos.setX(1.0)
            else:
                norm_pos.setX(max(min_x, min(max_x, norm_pos.x())))
                
            self.points[self.active_point_idx] = norm_pos
            self.update()
            self.curve_changed.emit()
            
    def mouseReleaseEvent(self, event):
        self.active_point_idx = -1
        self.update()
        
class ColorCurveDialog(BaseEffectDialog):
    def __init__(self, parent=None):
        super().__init__("Renk Eğrisi (Color Curve)", parent)
        
    def _build_ui(self):
        self.graph = CurveGraphWidget()
        self.graph.curve_changed.connect(self._emit_preview)
        self.layout.insertWidget(0, self.graph)
        
    def _get_args(self):
        points = [(p.x(), p.y()) for p in self.graph.points]
        
        def curve_func(val: float) -> float:
            if val <= points[0][0]: return points[0][1]
            if val >= points[-1][0]: return points[-1][1]
            
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i+1]
                if x1 <= val <= x2:
                    t = (val - x1) / (x2 - x1)
                    return y1 + t * (y2 - y1)
            return val
            
        return {"curve_func": curve_func}

class LightingEffectDialog(BaseEffectDialog):
    def __init__(self, parent=None):
        from PyQt6.QtWidgets import QTabWidget, QWidget, QComboBox
        self.QTabWidget = QTabWidget
        self.QWidget = QWidget
        self.QComboBox = QComboBox
        super().__init__("Aydınlatma (Lighting)", parent)
        
    def _build_ui(self):
        self.tabs = self.QTabWidget()
        self.layout.insertWidget(0, self.tabs)
        
        # --- BASIC TAB ---
        self.basic_tab = self.QWidget()
        basic_layout = QVBoxLayout(self.basic_tab)
        
        # Yön
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Işık Yönü:"))
        self.basic_dir_combo = self.QComboBox()
        self.basic_dir_combo.addItems([
            "Sol Üst (Top-Left)", "Üst (Top)", "Sağ Üst (Top-Right)",
            "Sol (Left)", "Merkez (Center)", "Sağ (Right)",
            "Sol Alt (Bottom-Left)", "Alt (Bottom)", "Sağ Alt (Bottom-Right)"
        ])
        self.basic_dir_combo.setCurrentIndex(0)
        self.basic_dir_combo.currentIndexChanged.connect(self._emit_preview)
        dir_layout.addWidget(self.basic_dir_combo)
        basic_layout.addLayout(dir_layout)
        
        # Parlaklık
        int_layout = QHBoxLayout()
        int_layout.addWidget(QLabel("Parlaklık:"))
        self.basic_intensity = QSlider(Qt.Orientation.Horizontal)
        self.basic_intensity.setRange(0, 100)
        self.basic_intensity.setValue(50)
        self.basic_int_val = QLabel("50")
        int_layout.addWidget(self.basic_intensity)
        int_layout.addWidget(self.basic_int_val)
        basic_layout.addLayout(int_layout)
        self.basic_intensity.valueChanged.connect(lambda val: self.basic_int_val.setText(str(val)))
        self.basic_intensity.valueChanged.connect(self._emit_preview)
        
        basic_layout.addStretch()
        self.tabs.addTab(self.basic_tab, "Basit (Basic)")
        
        # --- ADVANCED TAB ---
        self.adv_tab = self.QWidget()
        adv_layout = QVBoxLayout(self.adv_tab)
        
        def make_slider(layout, name, min_val, max_val, default_val):
            l = QHBoxLayout()
            l.addWidget(QLabel(name))
            s = QSlider(Qt.Orientation.Horizontal)
            s.setRange(min_val, max_val)
            s.setValue(default_val)
            v = QLabel(str(default_val))
            l.addWidget(s)
            l.addWidget(v)
            layout.addLayout(l)
            s.valueChanged.connect(lambda val, lbl=v: lbl.setText(str(val)))
            s.valueChanged.connect(self._emit_preview)
            return s
            
        self.lx_slider = make_slider(adv_layout, "Işık X:", -100, 100, 50)
        self.ly_slider = make_slider(adv_layout, "Işık Y:", -100, 100, -50)
        self.lz_slider = make_slider(adv_layout, "Işık Z:", -100, 100, 80)
        self.kd_slider = make_slider(adv_layout, "Lambertian (kd):", 0, 200, 80)
        self.ks_slider = make_slider(adv_layout, "Specular (ks):", 0, 200, 40)
        self.shine_slider = make_slider(adv_layout, "Parlama Keskinliği:", 1, 50, 10)
        self.bands_slider = make_slider(adv_layout, "Bant Sayısı:", 1, 8, 3)
        
        adv_layout.addStretch()
        self.tabs.addTab(self.adv_tab, "Gelişmiş (Advanced)")
        
        self.tabs.currentChanged.connect(self._emit_preview)

    def _get_args(self):
        if self.tabs.currentIndex() == 0:
            # Basic Mode
            dirs = {
                0: (50, -50, 80),   # Top-Left
                1: (0, -70, 80),    # Top
                2: (-50, -50, 80),  # Top-Right
                3: (70, 0, 80),     # Left
                4: (0, 0, 100),     # Center
                5: (-70, 0, 80),    # Right
                6: (50, 50, 80),    # Bottom-Left
                7: (0, 70, 80),     # Bottom
                8: (-50, 50, 80)    # Bottom-Right
            }
            idx = self.basic_dir_combo.currentIndex()
            lx, ly, lz = dirs.get(idx, (50, -50, 80))
            
            intensity = self.basic_intensity.value() / 50.0 # 0.0 to 2.0
            kd = 80 * intensity
            ks = 40 * intensity
            
            return {
                "lx": lx / 100.0,
                "ly": ly / 100.0,
                "lz": lz / 100.0,
                "kd": kd / 100.0,
                "ks": ks / 100.0,
                "shininess": 10.0,
                "num_bands": 3
            }
        else:
            # Advanced Mode
            return {
                "lx": self.lx_slider.value() / 100.0,
                "ly": self.ly_slider.value() / 100.0,
                "lz": self.lz_slider.value() / 100.0,
                "kd": self.kd_slider.value() / 100.0,
                "ks": self.ks_slider.value() / 100.0,
                "shininess": float(self.shine_slider.value()),
                "num_bands": self.bands_slider.value()
            }
