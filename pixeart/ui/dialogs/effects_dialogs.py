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
        t_layout.addWidget(self.btn_target)
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
