from enum import Enum, auto
from typing import Dict, Optional, List, Tuple
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from pixeart.core.color import Color
from pixeart.core.history import History, Command
from pixeart.core.document import Document
from .base_tool import BaseTool, BrushShape
from .pencil import PencilTool
from .eraser import EraserTool
from .color_picker import ColorPickerTool
from .fill import FillTool


class SymmetryMode(Enum):
    NONE = auto()
    VERTICAL = auto()
    HORIZONTAL = auto()
    BOTH = auto()


class ToolManager:
    """
    Tüm araçları, aktif renkleri ve fırça ayarlarını yöneten köprü sınıf.
    Arayüz (UI) doğrudan ToolManager ile konuşur.
    """
    def __init__(self, history: History):
        self.history = history
        self.document: Optional[Document] = None
        self.canvas_scene = None
        self.color_palette = None

        self.tools: Dict[str, BaseTool] = {
            "pencil": PencilTool(),
            "eraser": EraserTool(),
            "picker": ColorPickerTool(),
            "fill": FillTool()
        }

        for tool in self.tools.values():
            tool.manager = self

        self.active_tool_id = "pencil"
        self.brush_size = 1
        self.brush_shape = BrushShape.SQUARE

        self.primary_color = Color(0, 0, 0, 255)
        self.secondary_color = Color(255, 255, 255, 255)

        self.symmetry_mode = SymmetryMode.NONE

    def register_tool(self, tool_id: str, tool: BaseTool):
        tool.manager = self
        self.tools[tool_id] = tool

    @property
    def active_tool(self) -> BaseTool:
        return self.tools.get(self.active_tool_id, self.tools["pencil"])

    def set_document(self, document: Document):
        self.document = document

    def set_canvas_scene(self, scene):
        self.canvas_scene = scene

    def set_tool(self, tool_id: str):
        if tool_id in self.tools:
            self.active_tool_id = tool_id

    def set_primary_color(self, qt_color: QColor):
        self.primary_color = Color(qt_color.red(), qt_color.green(), qt_color.blue(), qt_color.alpha())

    def set_secondary_color(self, qt_color: QColor):
        self.secondary_color = Color(qt_color.red(), qt_color.green(), qt_color.blue(), qt_color.alpha())

    def get_active_color(self, button: Qt.MouseButton) -> Color:
        if button == Qt.MouseButton.RightButton:
            return self.secondary_color
        return self.primary_color

    def update_canvas_pixel(self, x: int, y: int, color: Optional[Color]):
        if self.canvas_scene:
            qt_color = QColor(0, 0, 0, 0) if color is None else QColor(*color.to_rgba_tuple())
            self.canvas_scene.draw_pixel(x, y, qt_color)

    def notify_color_picked(self, qt_color: QColor, button: Qt.MouseButton):
        if hasattr(self, 'color_palette') and self.color_palette:
            if button == Qt.MouseButton.LeftButton:
                self.color_palette.current_colors.set_primary(qt_color)
            elif button == Qt.MouseButton.RightButton:
                self.color_palette.current_colors.set_secondary(qt_color)

    def commit_command(self, command: Command):
        self.history.execute(command)

    # --- Simetri Hesaplaması ---
    def get_symmetry_points(self, x: int, y: int) -> List[Tuple[int, int]]:
        if not self.document or self.symmetry_mode == SymmetryMode.NONE:
            return [(x, y)]

        w, h = self.document.width, self.document.height
        points = {(x, y)}

        if self.symmetry_mode in (SymmetryMode.VERTICAL, SymmetryMode.BOTH):
            points.add((w - 1 - x, y))

        if self.symmetry_mode in (SymmetryMode.HORIZONTAL, SymmetryMode.BOTH):
            points.add((x, h - 1 - y))

        if self.symmetry_mode == SymmetryMode.BOTH:
            points.add((w - 1 - x, h - 1 - y))

        return list(points)

    # --- Olay (Event) Yönlendirmeleri ---
    def handle_press(self, x: int, y: int, button: Qt.MouseButton):
        # If right-click and a selection exists, clear it globally (user expectation)
        if button == Qt.MouseButton.RightButton:
            sel = self.tools.get('selection')
            if sel and getattr(sel, 'selection_pixels', None):
                sel.clear_selection()
                return

        self.active_tool.on_press(x, y, button)

    def handle_press_f(self, x: float, y: float, button: Qt.MouseButton):
        """Float-precision press handling. Route to selection tool with floats,
        otherwise fall back to integer handlers for other tools."""
        sel = self.tools.get('selection')
        if self.active_tool_id == 'selection' and sel:
            sel.on_press(x, y, button)
            return
        # fallback: convert to int for legacy tools
        self.handle_press(int(round(x)), int(round(y)), button)

    def handle_drag(self, x: int, y: int, button: Qt.MouseButton):
        self.active_tool.on_drag(x, y, button)

    def handle_drag_f(self, x: float, y: float, button: Qt.MouseButton):
        sel = self.tools.get('selection')
        if self.active_tool_id == 'selection' and sel:
            sel.on_drag(x, y, button)
            return
        self.handle_drag(int(round(x)), int(round(y)), button)

    def handle_release(self, x: int, y: int, button: Qt.MouseButton):
        self.active_tool.on_release(x, y, button)

    def handle_release_f(self, x: float, y: float, button: Qt.MouseButton):
        sel = self.tools.get('selection')
        if self.active_tool_id == 'selection' and sel:
            sel.on_release(x, y, button)
            return
        self.handle_release(int(round(x)), int(round(y)), button)
