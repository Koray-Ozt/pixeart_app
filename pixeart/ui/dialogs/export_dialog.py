from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QSpinBox, QPushButton, QFormLayout, QFileDialog, QCheckBox
)
from PyQt6.QtCore import Qt

from pixeart.core.document import Document
from PyQt6.QtGui import QImage, QPainter, QColor

class ExportDialog(QDialog):
    def __init__(self, document: Document, parent=None):
        super().__init__(parent)
        self.document = document
        self.document_width = document.width
        self.document_height = document.height
        
        self.setWindowTitle("Dışa Aktar")
        self.setFixedSize(400, 320)
        self.setModal(True)
        
        self.export_path = ""
        self.export_format = "PNG"
        self.export_scale = 100
        self.keep_transparency = True
        
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QLabel("Çizimi Dışa Aktar")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #e0e0e0;")
        layout.addWidget(header)
        
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setSpacing(12)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPG", "BMP"])
        self.format_combo.currentTextChanged.connect(self._update_format)
        form_layout.addRow("Format:", self.format_combo)
        
        scale_layout = QHBoxLayout()
        self.scale_spin = QSpinBox()
        self.scale_spin.setRange(10, 10000)
        self.scale_spin.setValue(100)
        self.scale_spin.setSuffix(" %")
        self.scale_spin.setSingleStep(100)
        self.scale_spin.valueChanged.connect(self._update_size_preview)
        
        self.size_preview = QLabel(f"({self.document_width} x {self.document_height} px)")
        self.size_preview.setStyleSheet("color: #888;")
        
        scale_layout.addWidget(self.scale_spin)
        scale_layout.addWidget(self.size_preview)
        form_layout.addRow("Ölçek:", scale_layout)
        
        self.bg_checkbox = QCheckBox("Şeffaf arka planı koru")
        self.bg_checkbox.setChecked(True)
        form_layout.addRow("Arka Plan:", self.bg_checkbox)
        
        layout.addLayout(form_layout)
        
        info_label = QLabel("Not: Ölçeklendirme işlemi Nearest Neighbor (kayıpsız) olarak yapılacaktır.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #a0a0a0; font-size: 11px; font-style: italic;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_export = QPushButton("Dosya Konumu Seç...")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setStyleSheet("background-color: #007acc; color: white; font-weight: bold; padding: 6px;")
        self.btn_export.clicked.connect(self._on_export_clicked)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_export)
        
        layout.addLayout(btn_layout)

    def _update_format(self, text: str):
        self.export_format = text
        if text in ["JPG", "BMP"]:
            self.bg_checkbox.setChecked(False)
            self.bg_checkbox.setEnabled(False)
        else:
            self.bg_checkbox.setEnabled(True)
            self.bg_checkbox.setChecked(True)

    def _update_size_preview(self, value: int):
        self.export_scale = value
        new_w = int(self.document_width * (value / 100.0))
        new_h = int(self.document_height * (value / 100.0))
        self.size_preview.setText(f"({new_w} x {new_h} px)")

    def _on_export_clicked(self):
        filter_str = f"{self.export_format} Image (*.{self.export_format.lower()})"
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Görseli Kaydet", 
            f"pixeart_cizim.{self.export_format.lower()}", 
            filter_str
        )
        
        if file_path:
            self.export_path = file_path
            self.keep_transparency = self.bg_checkbox.isChecked()
            self.accept()

    def export_image(self):
        if not self.export_path:
            return

        w, h = self.document.width, self.document.height
        image = QImage(w, h, QImage.Format.Format_ARGB32)
        if self.keep_transparency and self.export_format == "PNG":
            image.fill(QColor(0, 0, 0, 0))
        else:
            image.fill(QColor(255, 255, 255, 255))

        for layer in self.document.layers:
            if not layer.is_visible:
                continue
            for (x, y), color in layer.active_pixels.items():
                if not color.is_transparent:
                    image.setPixelColor(x, y, QColor(*color.to_rgba_tuple()))

        if self.export_scale != 100:
            new_w = int(w * (self.export_scale / 100.0))
            new_h = int(h * (self.export_scale / 100.0))
            image = image.scaled(new_w, new_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)

        image.save(self.export_path, self.export_format)
