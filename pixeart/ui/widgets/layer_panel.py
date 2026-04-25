from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QListWidget, QListWidgetItem, QLabel, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont

from pixeart.core.document import Document
from pixeart.core.layer import Layer


class LayerItemWidget(QWidget):
    visibility_toggled = pyqtSignal(bool)
    
    def __init__(self, layer: Layer, parent=None):
        super().__init__(parent)
        self.layer = layer
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.btn_visible = QPushButton("👁" if layer.is_visible else "✕")
        self.btn_visible.setFixedSize(24, 24)
        self.btn_visible.setCheckable(True)
        self.btn_visible.setChecked(layer.is_visible)
        self.btn_visible.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_visible.setStyleSheet("""
            QPushButton { border: none; font-size: 14px; background: transparent; }
            QPushButton:hover { background: #444; border-radius: 4px; }
        """)
        self.btn_visible.clicked.connect(self._on_visibility_clicked)
        
        self.lbl_name = QLabel(layer.name)
        self.lbl_name.setStyleSheet("color: white;")
        
        self.btn_lock = QPushButton("🔒" if layer.is_locked else "🔓")
        self.btn_lock.setFixedSize(24, 24)
        self.btn_lock.setCheckable(True)
        self.btn_lock.setChecked(layer.is_locked)
        self.btn_lock.setStyleSheet("QPushButton { border: none; font-size: 14px; background: transparent; }")
        
        layout.addWidget(self.btn_visible)
        layout.addWidget(self.lbl_name, stretch=1)
        layout.addWidget(self.btn_lock)
        
    def _on_visibility_clicked(self, checked: bool):
        self.layer.is_visible = checked
        self.btn_visible.setText("👁" if checked else "✕")
        self.visibility_toggled.emit(checked)
        
    def update_name(self, new_name: str):
        self.layer.name = new_name
        self.lbl_name.setText(new_name)


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
        
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list_widget.setStyleSheet("""
            QListWidget { background-color: #1e1e1e; border: 1px solid #333; border-radius: 4px; }
            QListWidget::item { border-bottom: 1px solid #2a2a2a; padding: 2px; }
            QListWidget::item:selected { background-color: #005a9e; }
        """)
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        layout.addWidget(self.list_widget)
        
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)
        
        self.btn_add = self._create_btn("+", "Yeni Katman Ekle")
        self.btn_add.clicked.connect(self.add_new_layer)
        
        self.btn_remove = self._create_btn("-", "Seçili Katmanı Sil")
        self.btn_remove.clicked.connect(self.remove_selected_layer)
        
        self.btn_up = self._create_btn("▲", "Katmanı Yukarı Taşı")
        self.btn_up.clicked.connect(self.move_layer_up)
        
        self.btn_down = self._create_btn("▼", "Katmanı Aşağı Taşı")
        self.btn_down.clicked.connect(self.move_layer_down)
        
        toolbar.addWidget(self.btn_add)
        toolbar.addWidget(self.btn_remove)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_up)
        toolbar.addWidget(self.btn_down)
        
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
            self.list_widget.blockSignals(False)
            return
            
        for i in reversed(range(len(self.document.layers))):
            layer = self.document.layers[i]
            
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 36))
            
            widget = LayerItemWidget(layer)
            widget.visibility_toggled.connect(lambda checked: self.layer_visibility_changed.emit())
            
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
            
        active_row = self._doc_idx_to_row(self.document.active_layer_index)
        if active_row >= 0:
            self.list_widget.setCurrentRow(active_row)
            
        self.list_widget.blockSignals(False)
        self.layer_structure_changed.emit()

    def _on_row_changed(self, row: int):
        if not self.document or row < 0:
            return
            
        idx = self._row_to_doc_idx(row)
        self.document.set_active_layer(idx)

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
        if not self.document:
            return
        
        new_idx = self.document.active_layer_index + 1
        new_name = f"Katman {len(self.document.layers) + 1}"
        new_layer = Layer(new_name)
        
        self.document.add_layer(new_layer, index=new_idx)
        self.refresh_list()

    def remove_selected_layer(self):
        if not self.document or len(self.document.layers) <= 1:
            return 
            
        idx = self.document.active_layer_index
        if idx >= 0:
            self.document.remove_layer(idx)
            self.refresh_list()

    def move_layer_up(self):
        if not self.document:
            return
        
        idx = self.document.active_layer_index
        if idx < len(self.document.layers) - 1: 
            self.document.move_layer_up(idx)
            self.refresh_list()

    def move_layer_down(self):
        if not self.document:
            return
            
        idx = self.document.active_layer_index
        if idx > 0: 
            self.document.move_layer_down(idx)
            self.refresh_list()
