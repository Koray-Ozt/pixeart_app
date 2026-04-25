from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QSpinBox, QPushButton, QFormLayout, QFrame
)
from PyQt6.QtCore import Qt

class NewFileDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni Dosya Oluştur")
        self.setFixedSize(380, 310)
        self.setModal(True)
        
        self.canvas_width = 32
        self.canvas_height = 32
        self.is_ratio_locked = True
        
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QLabel("Yeni Pixel Art Projesi")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #e0e0e0;")
        layout.addWidget(header)
        
        self.preset_combo = QComboBox()
        self.presets = {
            "32 x 32 (Standart Karakter)": (32, 32),
            "16 x 16 (Retro Sprite)": (16, 16),
            "64 x 64 (Detaylı Obje)": (64, 64),
            "128 x 128 (Büyük Portre)": (128, 128),
            "Özel Çözünürlük...": None
        }
        self.preset_combo.addItems(self.presets.keys())
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        
        layout.addWidget(QLabel("Şablonlar:"))
        layout.addWidget(self.preset_combo)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #333; margin: 5px 0px;")
        layout.addWidget(line)
        
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 4096)
        self.width_spin.setValue(32)
        self.width_spin.setSuffix(" px")
        self.width_spin.valueChanged.connect(self._on_width_changed)
        form_layout.addRow("Genişlik (W):", self.width_spin)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 4096)
        self.height_spin.setValue(32)
        self.height_spin.setSuffix(" px")
        self.height_spin.valueChanged.connect(self._on_height_changed)
        form_layout.addRow("Yükseklik (H):", self.height_spin)
        
        self.lock_btn = QPushButton("🔒 Kare Orantıyı Koru")
        self.lock_btn.setCheckable(True)
        self.lock_btn.setChecked(True)
        self.lock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lock_btn.setStyleSheet("""
            QPushButton { 
                background-color: #2b2b2b; color: #888; 
                border: 1px solid #444; border-radius: 4px; padding: 4px; 
            }
            QPushButton:checked { 
                background-color: #007acc; color: white; 
                border: 1px solid #005a9e; font-weight: bold;
            }
        """)
        self.lock_btn.toggled.connect(self._on_lock_toggled)
        form_layout.addRow("", self.lock_btn)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_create = QPushButton("Oluştur")
        self.btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_create.setStyleSheet("background-color: #007acc; color: white; font-weight: bold; padding: 6px 20px;")
        self.btn_create.clicked.connect(self._on_create_clicked)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_create)
        
        layout.addLayout(btn_layout)

    def _on_preset_changed(self, text: str):
        size = self.presets.get(text)
        if size is not None:
            self.width_spin.blockSignals(True)
            self.height_spin.blockSignals(True)
            self.width_spin.setValue(size[0])
            self.height_spin.setValue(size[1])
            self.width_spin.blockSignals(False)
            self.height_spin.blockSignals(False)

    def _on_width_changed(self, value: int):
        self._set_custom_preset()
        if self.is_ratio_locked:
            self.height_spin.blockSignals(True)
            self.height_spin.setValue(value)
            self.height_spin.blockSignals(False)

    def _on_height_changed(self, value: int):
        self._set_custom_preset()
        if self.is_ratio_locked:
            self.width_spin.blockSignals(True)
            self.width_spin.setValue(value)
            self.width_spin.blockSignals(False)
            
    def _on_lock_toggled(self, checked: bool):
        self.is_ratio_locked = checked
        if checked:
            self.lock_btn.setText("🔒 Kare Orantıyı Koru")
            self.height_spin.blockSignals(True)
            self.height_spin.setValue(self.width_spin.value())
            self.height_spin.blockSignals(False)
        else:
            self.lock_btn.setText("🔓 Serbest Boyut")

    def _set_custom_preset(self):
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentText("Özel Çözünürlük...")
        self.preset_combo.blockSignals(False)

    def _on_create_clicked(self):
        self.canvas_width = self.width_spin.value()
        self.canvas_height = self.height_spin.value()
        self.accept()
