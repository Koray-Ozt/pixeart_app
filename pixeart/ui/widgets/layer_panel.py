from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QListWidget, QListWidgetItem, QLabel, QInputDialog, QSlider, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap, QImage, QColor

from pixeart.core.document import Document
from pixeart.core.layer import Layer


class LayerItemWidget(QWidget):
    visibility_toggled = pyqtSignal(bool)
    lock_toggled = pyqtSignal(bool)
    
    def __init__(self, layer: Layer, parent=None):
        super().__init__(parent)
        self.layer = layer
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Visibility
        self.btn_visible = QPushButton("👁" if layer.is_visible else "✕")
        self.btn_visible.setFixedSize(24, 24)
        self.btn_visible.setCheckable(True)
        self.btn_visible.setChecked(layer.is_visible)
        self.btn_visible.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_visible.setStyleSheet("QPushButton { border: none; font-size: 14px; background: transparent; color: white; } QPushButton:hover { background: #444; border-radius: 4px; }")
        self.btn_visible.clicked.connect(self._on_visibility_clicked)
        
        # Thumbnail
        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(32, 32)
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail.setStyleSheet("background-color: white; border: 1px solid #666; border-radius: 2px;")
        
        # Name
        self.lbl_name = QLabel(layer.name)
        self.lbl_name.setWordWrap(True)
        self.lbl_name.setStyleSheet("color: white;")
        
        # Lock
        self.btn_lock = QPushButton("🔒" if layer.is_locked else "🔓")
        self.btn_lock.setFixedSize(24, 24)
        self.btn_lock.setCheckable(True)
        self.btn_lock.setChecked(layer.is_locked)
        self.btn_lock.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lock.setStyleSheet("QPushButton { border: none; font-size: 14px; background: transparent; color: white; } QPushButton:hover { background: #444; border-radius: 4px; }")
        self.btn_lock.clicked.connect(self._on_lock_clicked)
        
        layout.addWidget(self.btn_visible)
        layout.addWidget(self.thumbnail)
        layout.addWidget(self.lbl_name, stretch=1)
        layout.addWidget(self.btn_lock)
        
    def _on_visibility_clicked(self, checked: bool):
        self.layer.is_visible = checked
        self.btn_visible.setText("👁" if checked else "✕")
        self.visibility_toggled.emit(checked)
        
    def _on_lock_clicked(self, checked: bool):
        self.layer.is_locked = checked
        self.btn_lock.setText("🔒" if checked else "🔓")
        self.lock_toggled.emit(checked)
        
    def update_name(self, new_name: str):
        self.layer.name = new_name
        self.lbl_name.setText(new_name)
        
    def update_thumbnail(self, doc_width: int, doc_height: int):
        if doc_width <= 0 or doc_height <= 0:
            return
            
        img = QImage(doc_width, doc_height, QImage.Format.Format_ARGB32)
        img.fill(QColor(0, 0, 0, 0))
        
        for (x, y), color in self.layer.active_pixels.items():
            if not color.is_transparent:
                img.setPixelColor(x, y, QColor(*color.to_rgba_tuple()))
                
        pixmap = QPixmap.fromImage(img).scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
        self.thumbnail.setPixmap(pixmap)


class LayerPanel(QWidget):
    layer_structure_changed = pyqtSignal()
    layer_visibility_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.document: Document = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # --- Top Controls: Opacity & Blend Mode ---
        top_layout = QHBoxLayout()
        top_layout.setSpacing(5)
        
        lbl_op = QLabel("Opaklık:")
        lbl_op.setStyleSheet("color: #ccc; font-size: 11px;")
        
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setEnabled(False)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        
        self.blend_combo = QComboBox()
        self.blend_combo.addItems(["Normal", "Multiply", "Screen"])
        self.blend_combo.setEnabled(False)
        self.blend_combo.currentTextChanged.connect(self._on_blend_changed)
        self.blend_combo.setStyleSheet("QComboBox { background: #333; color: white; border-radius: 2px; }")
        
        top_layout.addWidget(lbl_op)
        top_layout.addWidget(self.opacity_slider)
        top_layout.addWidget(self.blend_combo)
        layout.addLayout(top_layout)
        
        # --- List Widget ---
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list_widget.setDragEnabled(True)
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.list_widget.setStyleSheet("""
            QListWidget { background-color: #1e1e1e; border: 1px solid #333; border-radius: 4px; }
            QListWidget::item { border-bottom: 1px solid #2a2a2a; padding: 2px; }
            QListWidget::item:selected { background-color: #005a9e; }
        """)
        
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.model().rowsMoved.connect(self._on_rows_moved)
        
        layout.addWidget(self.list_widget)
        
        # Toolbar (Aşağıdaki butonlar)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)
        
        self.btn_add = self._create_btn("+", "Yeni Katman Ekle")
        self.btn_add.clicked.connect(self.add_new_layer)
        
        self.btn_remove = self._create_btn("-", "Seçili Katmanı Sil")
        self.btn_remove.clicked.connect(self.remove_selected_layer)
        
        toolbar.addWidget(self.btn_add)
        toolbar.addWidget(self.btn_remove)
        toolbar.addStretch()
        layout.addLayout(toolbar)

    def _create_btn(self, text: str, tooltip: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(28, 28)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton { background: #333; color: white; border-radius: 4px; border: 1px solid #444; font-size: 14px;}
            QPushButton:hover { background: #4a4a4a; border: 1px solid #666; }
            QPushButton:pressed { background: #222; }
        """)
        return btn

    def set_document(self, document: Document):
        self.document = document
        self.refresh_list()

    def update_thumbnails(self):
        if not self.document: return
        w, h = self.document.width, self.document.height
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if isinstance(widget, LayerItemWidget):
                widget.update_thumbnail(w, h)

    def _on_rows_moved(self, parent, start, end, destination, row):
        if not self.document: return
        
        new_layers = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if isinstance(widget, LayerItemWidget):
                new_layers.append(widget.layer)
                
        # List widget üstten alta gösterir, Document ise alttan üste saklar.
        new_layers.reverse()
        
        active_layer = self.document.active_layer
        
        # Document içindeki listeyi doğrudan güncelleyelim
        self.document._layers = new_layers
        if active_layer in new_layers:
            self.document._active_layer_index = new_layers.index(active_layer)
            
        self.layer_structure_changed.emit()

    def _doc_idx_to_row(self, index: int) -> int:
        if not self.document or len(self.document.layers) == 0:
            return -1
        return len(self.document.layers) - 1 - index

    def _row_to_doc_idx(self, row: int) -> int:
        if not self.document or len(self.document.layers) == 0:
            return -1
        return len(self.document.layers) - 1 - row

    def refresh_list(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        
        if not self.document:
            self.opacity_slider.setEnabled(False)
            self.blend_combo.setEnabled(False)
            self.list_widget.blockSignals(False)
            return
            
        w, h = self.document.width, self.document.height
        
        for i in reversed(range(len(self.document.layers))):
            layer = self.document.layers[i]
            
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 44))
            
            widget = LayerItemWidget(layer)
            widget.update_thumbnail(w, h)
            widget.visibility_toggled.connect(lambda checked: self.layer_visibility_changed.emit())
            widget.lock_toggled.connect(lambda checked: self.layer_structure_changed.emit())
            
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
            
        active_row = self._doc_idx_to_row(self.document.active_layer_index)
        if active_row >= 0:
            self.list_widget.setCurrentRow(active_row)
            self._update_top_controls()
            
        self.list_widget.blockSignals(False)
        self.layer_structure_changed.emit()

    def _update_top_controls(self):
        if not self.document: return
        layer = self.document.active_layer
        if layer:
            self.opacity_slider.setEnabled(True)
            self.blend_combo.setEnabled(True)
            
            self.opacity_slider.blockSignals(True)
            self.blend_combo.blockSignals(True)
            
            self.opacity_slider.setValue(int(layer.opacity * 100))
            blend = getattr(layer, 'blend_mode', 'Normal')
            idx = self.blend_combo.findText(blend)
            if idx >= 0:
                self.blend_combo.setCurrentIndex(idx)
                
            self.opacity_slider.blockSignals(False)
            self.blend_combo.blockSignals(False)

    def _on_row_changed(self, row: int):
        if not self.document or row < 0:
            self.opacity_slider.setEnabled(False)
            self.blend_combo.setEnabled(False)
            return
            
        idx = self._row_to_doc_idx(row)
        self.document.set_active_layer(idx)
        self._update_top_controls()

    def _on_opacity_changed(self, value: int):
        if self.document and self.document.active_layer:
            self.document.active_layer.opacity = value / 100.0
            self.layer_visibility_changed.emit()
            
    def _on_blend_changed(self, text: str):
        if self.document and self.document.active_layer:
            self.document.active_layer.blend_mode = text
            self.layer_visibility_changed.emit()

    def _on_item_double_clicked(self, item: QListWidgetItem):
        row = self.list_widget.row(item)
        idx = self._row_to_doc_idx(row)
        layer = self.document.layers[idx]
        
        new_name, ok = QInputDialog.getText(self, "Katmanı Yeniden Adlandır", "Yeni İsim:", text=layer.name)
        if ok and new_name.strip():
            widget = self.list_widget.itemWidget(item)
            if isinstance(widget, LayerItemWidget):
                widget.update_name(new_name.strip())

    def add_new_layer(self):
        if not self.document: return
        new_idx = self.document.active_layer_index + 1
        new_name = f"Katman {len(self.document.layers) + 1}"
        new_layer = Layer(new_name)
        self.document.add_layer(new_layer, index=new_idx)
        self.refresh_list()

    def remove_selected_layer(self):
        if not self.document or len(self.document.layers) <= 1: return 
        idx = self.document.active_layer_index
        if idx >= 0:
            self.document.remove_layer(idx)
            self.refresh_list()
