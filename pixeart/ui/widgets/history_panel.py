from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel
from PyQt6.QtCore import Qt, pyqtSignal

class HistoryPanel(QWidget):
    # (index, is_undo) -> sinyallerini yayınlayabiliriz, ama history sisteminde 
    # belirli bir index'e atlamak için history.py'yi genişletmemiz gerekir.
    # Şimdilik sadece history listesini gösterip güncel tutacağız, ve belki 
    # item'a tıklanınca aradaki işlemleri undo/redo yapacağız.
    
    history_jump_requested = pyqtSignal(int)
    
    def __init__(self, history, parent=None):
        super().__init__(parent)
        self.history = history
        self.setMinimumWidth(200)
        self.setStyleSheet("""
            QWidget { background-color: #2b2b2b; color: white; }
            QListWidget { background-color: #1e1e1e; border: 1px solid #444; border-radius: 4px; outline: 0; }
            QListWidget::item { padding: 4px 8px; border-bottom: 1px solid #333; }
            QListWidget::item:selected { background-color: #005a9e; color: white; }
            QListWidget::item:hover:!selected { background-color: #3d3d3d; }
            QLabel { font-weight: bold; padding-bottom: 4px; }
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        
        title = QLabel("Geçmiş (History)")
        self.layout.addWidget(title)
        
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.layout.addWidget(self.list_widget)
        
        self.refresh()
        
    def refresh(self):
        self.list_widget.clear()
        
        # Orijinal state (Initial)
        item = QListWidgetItem("Orijinal Durum")
        item.setData(Qt.ItemDataRole.UserRole, -1)
        self.list_widget.addItem(item)
        
        # Undo stack'indekiler (Yapılmış ve aktif olanlar)
        for i, cmd in enumerate(self.history._undo_stack):
            item = QListWidgetItem(cmd.name)
            item.setData(Qt.ItemDataRole.UserRole, i) # undo stack index
            self.list_widget.addItem(item)
            
        # Redo stack'indekiler (Geri alınmış, gri görünmeli)
        # Redo stack LIFO (Last In First Out) olduğu için ters sırada eklenmeli
        current_undo_count = len(self.history._undo_stack)
        for i, cmd in enumerate(reversed(self.history._redo_stack)):
            item = QListWidgetItem(f"[Geri Alındı] {cmd.name}")
            item.setForeground(Qt.GlobalColor.gray)
            item.setData(Qt.ItemDataRole.UserRole, current_undo_count + i) # redo stack index (sanal)
            self.list_widget.addItem(item)
            
        # Şu anki konumu seçili yap
        if self.list_widget.count() > 0:
            current_idx = len(self.history._undo_stack)
            self.list_widget.setCurrentRow(current_idx)
            
    def _on_item_clicked(self, item):
        target_idx = item.data(Qt.ItemDataRole.UserRole)
        current_idx = len(self.history._undo_stack) - 1
        
        if target_idx == current_idx:
            return
            
        if target_idx < current_idx:
            # Geri al (Undo)
            diff = current_idx - target_idx
            for _ in range(diff):
                self.history.undo()
        else:
            # İleri al (Redo)
            diff = target_idx - current_idx
            for _ in range(diff):
                self.history.redo()
                
        # History objesi zaten notify çağırıp refresh'i tetikleyecek (main_window üzerinden)
