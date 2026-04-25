from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QButtonGroup, 
    QLabel, QSpinBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal

class ToolBarWidget(QWidget):
    tool_changed = pyqtSignal(str) 
    brush_size_changed = pyqtSignal(int)
    brush_shape_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(72) 
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 15, 4, 15)
        layout.setSpacing(12)
        
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        self.btn_group.buttonClicked.connect(self._on_tool_clicked)
        
        tools = [
            ("P", "pencil", "Kalem (B)"),
            ("E", "eraser", "Silgi (E)"),
            ("F", "fill", "Boya Kovası (G)"),
            ("I", "picker", "Renk Seçici (I)"),
            ("H", "pan", "Kaydırma (H)"),
            ("Z", "zoom", "Yakınlaştırma (Z)")
        ]
        
        self.tool_map = {} 
        
        for i, (icon, code, tooltip) in enumerate(tools):
            btn = QPushButton(icon)
            btn.setFixedSize(36, 36)
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: 2px solid transparent;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: bold;
                    color: #ccc;
                }
                QPushButton:hover {
                    background-color: #2a2a2a;
                    color: white;
                }
                QPushButton:checked {
                    background-color: #005a9e;
                    border: 2px solid #66b2ff;
                    color: white;
                }
            """)
            
            self.btn_group.addButton(btn, i) 
            self.tool_map[btn] = code
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
            
            if code == "pencil":
                btn.setChecked(True)
                
        layout.addSpacing(10)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #333;")
        layout.addWidget(line)
        layout.addSpacing(10)
        
        lbl_size = QLabel("Boyut")
        lbl_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_size.setStyleSheet("color: #888; font-size: 11px; font-weight: bold;")
        layout.addWidget(lbl_size)
        
        self.spin_size = QSpinBox()
        self.spin_size.setRange(1, 64) 
        self.spin_size.setValue(1)
        self.spin_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.spin_size.setStyleSheet("""
            QSpinBox {
                background-color: #1e1e1e;
                color: #fff;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 1px solid #005a9e;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 0px;
            }
        """)
        self.spin_size.valueChanged.connect(self.brush_size_changed.emit)
        layout.addWidget(self.spin_size)
        
        layout.addSpacing(5)
        
        # Fırça Şekli (Kare / Daire) Butonu
        self.btn_shape = QPushButton("■")
        self.btn_shape.setToolTip("Fırça Şekli: Kare")
        self.btn_shape.setFixedSize(44, 30)
        self.btn_shape.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_shape.setStyleSheet("""
            QPushButton {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 4px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #333;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        self.btn_shape.clicked.connect(self._toggle_brush_shape)
        self.current_shape = "square"
        layout.addWidget(self.btn_shape, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        layout.addStretch()

    def _toggle_brush_shape(self):
        if self.current_shape == "square":
            self.current_shape = "circle"
            self.btn_shape.setText("●")
            self.btn_shape.setToolTip("Fırça Şekli: Daire")
        else:
            self.current_shape = "square"
            self.btn_shape.setText("■")
            self.btn_shape.setToolTip("Fırça Şekli: Kare")
            
        self.brush_shape_changed.emit(self.current_shape)

    def _on_tool_clicked(self, button):
        tool_code = self.tool_map.get(button)
        if tool_code:
            self.tool_changed.emit(tool_code)
            
    def select_tool(self, code: str):
        for btn, btn_code in self.tool_map.items():
            if btn_code == code:
                btn.setChecked(True)
                self._on_tool_clicked(btn)
                break
            
    def get_current_brush_size(self) -> int:
        return self.spin_size.value()

