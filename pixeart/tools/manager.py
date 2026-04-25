from typing import Dict, Optional
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

class ToolManager:
    """
    Tüm araçları, aktif renkleri ve fırça ayarlarını yöneten köprü sınıf.
    Arayüz (UI) doğrudan ToolManager ile konuşur.
    """
    def __init__(self, history: History):
        self.history = history
        self.document: Optional[Document] = None
        self.canvas_scene = None # UI Canvas referansı
        self.color_palette = None # UI Color Palette referansı
        
        # Kayıtlı araçlar
        self.tools: Dict[str, BaseTool] = {
            "pencil": PencilTool(),
            "eraser": EraserTool(),
            "picker": ColorPickerTool(),
            "fill": FillTool()
        }
        
        # Bağımlılık (Dependency) Enjeksiyonu
        for tool in self.tools.values():
            tool.manager = self
            
        self.active_tool_id = "pencil"
        self.brush_size = 1
        self.brush_shape = BrushShape.SQUARE
        
        self.primary_color = Color(0, 0, 0, 255)
        self.secondary_color = Color(255, 255, 255, 255)
        
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
        # Sol tık = Birincil Renk, Sağ tık veya Orta = İkincil Renk
        if button == Qt.MouseButton.RightButton:
            return self.secondary_color
        return self.primary_color
        
    def update_canvas_pixel(self, x: int, y: int, color: Optional[Color]):
        """Çizim sırasında arayüzü (CanvasScene) kasmadan anında günceller."""
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
        """Fırça darbesi (Stroke) tamamlandığında geri alınabilir işlem olarak kaydeder."""
        # Undo stack'e basıp sistemi notify eder.
        self.history.execute(command)
        
    # --- Olay (Event) Yönlendirmeleri ---
    def handle_press(self, x: int, y: int, button: Qt.MouseButton):
        self.active_tool.on_press(x, y, button)
        
    def handle_drag(self, x: int, y: int, button: Qt.MouseButton):
        self.active_tool.on_drag(x, y, button)
        
    def handle_release(self, x: int, y: int, button: Qt.MouseButton):
        self.active_tool.on_release(x, y, button)
