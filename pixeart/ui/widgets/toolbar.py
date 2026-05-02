from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QButtonGroup,
    QLabel, QSpinBox, QFrame, QHBoxLayout, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal


class ToolBarWidget(QWidget):
    tool_changed = pyqtSignal(str)
    brush_size_changed = pyqtSignal(int)
    brush_shape_changed = pyqtSignal(str)
    grid_visible_changed = pyqtSignal(bool)
    tile_grid_visible_changed = pyqtSignal(bool)
    tile_size_changed = pyqtSignal(int)
    symmetry_changed = pyqtSignal(str)
    selection_mode_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        self.btn_group.buttonClicked.connect(self._on_tool_clicked)

        tools = [
            ("pencil.png", "pencil", "Kalem (B)"),
            ("eraser.png", "eraser", "Silgi (E)"),
            ("bucket.png", "fill", "Boya Kovası (G)"),
            ("picker.png", "picker", "Renk Seçici (I)"),
            ("select.png", "selection", "Seçim (M)"),
        ]

        self.tool_map = {}
        import os
        icon_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resources", "icons")

        for i, (icon_file, code, tooltip) in enumerate(tools):
            from PyQt6.QtGui import QIcon
            from PyQt6.QtCore import QSize
            
            icon_path = os.path.join(icon_dir, icon_file)
            btn = QPushButton()
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
                btn.setIconSize(QSize(20, 20))
            else:
                btn.setText(code[0].upper())
                
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(32, 32)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: 1px solid transparent;
                    border-radius: 6px;
                    padding: 4px;
                }
                QPushButton:hover { 
                    background-color: #3a3a3c; 
                    border: 1px solid #444; 
                }
                QPushButton:checked { 
                    background-color: #005a9e; 
                    border: 1px solid #66b2ff; 
                }
            """)
            self.btn_group.addButton(btn, i)
            self.tool_map[btn] = code
            layout.addWidget(btn)
            if code == "pencil":
                btn.setChecked(True)

        self._add_sep(layout)

        # --- Fırça Boyutu ---
        self.spin_size = QSpinBox()
        self.spin_size.setRange(1, 64)
        self.spin_size.setValue(1)
        self.spin_size.setFixedWidth(50)
        self.spin_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_size.setToolTip("Fırça Boyutu")
        self.spin_size.setStyleSheet("""
            QSpinBox { background-color: #1e1e1e; color: #fff; border: 1px solid #444;
                border-radius: 4px; padding: 2px; font-size: 13px; font-weight: bold; }
            QSpinBox:focus { border: 1px solid #005a9e; }
            QSpinBox::up-button, QSpinBox::down-button { width: 0px; }
        """)
        self.spin_size.valueChanged.connect(self.brush_size_changed.emit)
        layout.addWidget(self.spin_size)

        # --- Fırça Şekli ---
        self.btn_shape = QPushButton("■")
        self.btn_shape.setToolTip("Fırça Şekli: Kare")
        self.btn_shape.setFixedSize(32, 32)
        self.btn_shape.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_shape.setStyleSheet("""
            QPushButton { background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #444;
                border-radius: 4px; font-size: 16px; }
            QPushButton:hover { background-color: #333; }
        """)
        self.btn_shape.clicked.connect(self._toggle_brush_shape)
        self.current_shape = "square"
        layout.addWidget(self.btn_shape)

        self._add_sep(layout)

        # --- Seçim Modu ---
        self.combo_sel_mode = QComboBox()
        self.combo_sel_mode.addItems(["Dikdörtgen", "Lasso", "Daire"])
        self.combo_sel_mode.setFixedWidth(80)
        self.combo_sel_mode.setStyleSheet("QComboBox { background:#1e1e1e; color:white; border:1px solid #444; border-radius:2px; font-size:11px; }")
        self.combo_sel_mode.currentIndexChanged.connect(self._on_sel_mode_changed)
        layout.addWidget(self.combo_sel_mode)

        self._add_sep(layout)

        # --- Simetri Modu ---
        self.btn_symmetry = QPushButton("✕")
        self.btn_symmetry.setToolTip("Simetri Modu")
        self.btn_symmetry.setFixedSize(32, 32)
        self.btn_symmetry.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_symmetry.setStyleSheet("""
            QPushButton { background-color: #1e1e1e; color: #aaa; border: 1px solid #444;
                border-radius: 4px; font-size: 14px; }
            QPushButton:hover { background-color: #333; color: white; }
        """)
        self.btn_symmetry.clicked.connect(self._cycle_symmetry)
        self._symmetry_state = 0
        layout.addWidget(self.btn_symmetry)

        self._add_sep(layout)

        # --- Grid Kontrolleri ---
        self.btn_grid = QPushButton("▦")
        self.btn_grid.setCheckable(True)
        self.btn_grid.setChecked(True)
        self.btn_grid.setFixedSize(32, 32)
        self.btn_grid.setToolTip("Piksel Izgarası")
        self.btn_grid.setStyleSheet("""
            QPushButton { background:#1e1e1e; color:#aaa; border:1px solid #444; border-radius:4px; font-size:16px; }
            QPushButton:checked { background:#005a9e; color:white; border:1px solid #66b2ff; }
        """)
        self.btn_grid.toggled.connect(self.grid_visible_changed.emit)
        layout.addWidget(self.btn_grid)

        self.btn_tile = QPushButton("⊞")
        self.btn_tile.setCheckable(True)
        self.btn_tile.setChecked(True)
        self.btn_tile.setFixedSize(32, 32)
        self.btn_tile.setToolTip("Tile Izgarası")
        self.btn_tile.setStyleSheet("""
            QPushButton { background:#1e1e1e; color:#aaa; border:1px solid #444; border-radius:4px; font-size:16px; }
            QPushButton:checked { background:#0f3460; color:white; border:1px solid #5588cc; }
        """)
        self.btn_tile.toggled.connect(self.tile_grid_visible_changed.emit)
        layout.addWidget(self.btn_tile)

        self.spin_tile = QSpinBox()
        self.spin_tile.setRange(2, 128)
        self.spin_tile.setValue(16)
        self.spin_tile.setFixedWidth(50)
        self.spin_tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_tile.setToolTip("Tile Boyutu")
        self.spin_tile.setStyleSheet("""
            QSpinBox { background:#1e1e1e; color:#fff; border:1px solid #444; border-radius:3px;
                padding:2px; font-size:12px; }
            QSpinBox::up-button, QSpinBox::down-button { width:0px; }
        """)
        self.spin_tile.valueChanged.connect(self.tile_size_changed.emit)
        layout.addWidget(self.spin_tile)

        layout.addStretch()

    @staticmethod
    def _add_sep(layout):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("background-color: #333; margin: 4px 2px;")
        layout.addWidget(line)

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

    _SYM_CYCLE = [
        ("✕", "none", "Simetri: Kapalı"),
        ("↕", "vertical", "Simetri: Dikey"),
        ("↔", "horizontal", "Simetri: Yatay"),
        ("✦", "both", "Simetri: Her İkisi"),
    ]

    def _cycle_symmetry(self):
        self._symmetry_state = (self._symmetry_state + 1) % len(self._SYM_CYCLE)
        icon, mode, tip = self._SYM_CYCLE[self._symmetry_state]
        self.btn_symmetry.setText(icon)
        self.btn_symmetry.setToolTip(tip)
        self.symmetry_changed.emit(mode)

    def _on_sel_mode_changed(self, index):
        modes = ["rect", "lasso", "circle"]
        if 0 <= index < len(modes):
            self.selection_mode_changed.emit(modes[index])

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
