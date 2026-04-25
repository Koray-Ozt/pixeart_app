from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QPushButton, QColorDialog, QLabel, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QMouseEvent, QPen

DB16_COLORS = [
    "#140c1c", "#442434", "#30346d", "#4e4a4e",
    "#854c30", "#346524", "#d04648", "#757161",
    "#597dce", "#d27d2c", "#8595a1", "#6daa2c",
    "#d2aa99", "#6dc2ca", "#dad45e", "#deeed6"
]

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
        self.primary_color = color
        self.primary_changed.emit(color)
        self.update()
        
    def set_secondary(self, color: QColor):
        self.secondary_color = color
        self.secondary_changed.emit(color)
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
        if event.button() == Qt.MouseButton.LeftButton:
            color = QColorDialog.getColor(self.primary_color, self, "Birincil Rengi Seç")
            if color.isValid():
                self.set_primary(color)
        elif event.button() == Qt.MouseButton.RightButton:
            color = QColorDialog.getColor(self.secondary_color, self, "İkincil Rengi Seç")
            if color.isValid():
                self.set_secondary(color)
        event.accept()


class ColorPalette(QWidget):
    primary_color_changed = pyqtSignal(QColor)
    secondary_color_changed = pyqtSignal(QColor)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        top_layout = QHBoxLayout()
        self.current_colors = CurrentColorsWidget()
        self.current_colors.primary_changed.connect(self.primary_color_changed)
        self.current_colors.secondary_changed.connect(self.secondary_color_changed)
        
        self.btn_swap = QPushButton("Swap")
        self.btn_swap.setFixedSize(40, 24)
        self.btn_swap.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_swap.setStyleSheet("""
            QPushButton { background: #333; color: white; border-radius: 4px; border: 1px solid #444; }
            QPushButton:hover { background: #444; border: 1px solid #666; }
        """)
        self.btn_swap.clicked.connect(self.swap_colors)
        
        top_layout.addWidget(self.current_colors)
        swap_layout = QVBoxLayout()
        swap_layout.addWidget(self.btn_swap)
        swap_layout.addStretch()
        top_layout.addLayout(swap_layout)
        
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #333;")
        layout.addWidget(line)
        
        swatch_label = QLabel("Palet (DB16)")
        swatch_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(swatch_label)
        
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(4)
        
        for i, hex_color in enumerate(DB16_COLORS):
            row = i // 4
            col = i % 4
            swatch = SwatchItem(hex_color)
            swatch.clicked.connect(self._on_swatch_clicked)
            self.grid_layout.addWidget(swatch, row, col)
            
        layout.addLayout(self.grid_layout)
        layout.addStretch()

    def _on_swatch_clicked(self, color: QColor, button: Qt.MouseButton):
        if button == Qt.MouseButton.LeftButton:
            self.current_colors.set_primary(color)
        elif button == Qt.MouseButton.RightButton:
            self.current_colors.set_secondary(color)
            
    def swap_colors(self):
        p = self.current_colors.primary_color
        s = self.current_colors.secondary_color
        self.current_colors.set_primary(s)
        self.current_colors.set_secondary(p)

    def get_primary_color(self) -> QColor:
        return self.current_colors.primary_color
        
    def get_secondary_color(self) -> QColor:
        return self.current_colors.secondary_color
