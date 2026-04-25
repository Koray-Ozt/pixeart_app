from typing import Dict, Tuple, Optional
from PyQt6.QtCore import Qt
from pixeart.core.color import Color
from pixeart.core.commands import DrawCommand
from .base_tool import BaseTool

class PencilTool(BaseTool):
    """
    Kalem Aracı (Pencil Tool)
    Kullanıcının seçtiği birincil veya ikincil renk ile pikselleri boyar.
    Interpolasyon (Bresenham) kullanarak boşluksuz çizim yapar.
    """
    def __init__(self):
        super().__init__()
        self.is_drawing = False
        self.last_pos = None
        self.before_pixels: Dict[Tuple[int, int], Optional[Color]] = {}
        self.after_pixels: Dict[Tuple[int, int], Optional[Color]] = {}

    def on_press(self, x: int, y: int, button: Qt.MouseButton) -> None:
        if not self.manager or not self.manager.document:
            return
            
        self.is_drawing = True
        self.before_pixels.clear()
        self.after_pixels.clear()
        self.last_pos = (x, y)
        self._apply_brush(x, y, button)

    def on_drag(self, x: int, y: int, button: Qt.MouseButton) -> None:
        if not self.is_drawing or not self.last_pos:
            return
            
        pixels_to_draw = self._interpolate_line(self.last_pos[0], self.last_pos[1], x, y)
        for px, py in pixels_to_draw:
            self._apply_brush(px, py, button)
            
        self.last_pos = (x, y)

    def on_release(self, x: int, y: int, button: Qt.MouseButton) -> None:
        if not self.is_drawing or not self.manager:
            return
            
        self.is_drawing = False
        self.last_pos = None
        
        # En az bir piksel boyandıysa bunu Geçmişe (History) kaydet
        if self.after_pixels:
            layer_idx = self.manager.document.active_layer_index
            command = DrawCommand(
                document=self.manager.document,
                layer_index=layer_idx,
                before_pixels=self.before_pixels.copy(),
                after_pixels=self.after_pixels.copy()
            )
            self.manager.commit_command(command)
            
    def _apply_brush(self, cx: int, cy: int, button: Qt.MouseButton) -> None:
        """Piksel art motorunun en çok çalışan fonksiyonu: Fırçayı vurur."""
        doc = self.manager.document
        layer_idx = doc.active_layer_index
        if layer_idx < 0 or layer_idx >= len(doc.layers):
            return
            
        layer = doc.layers[layer_idx]
        if not layer.is_visible or layer.is_locked:
            return # Görünmez veya kilitli katmana çizim yapılamaz
            
        color = self.manager.get_active_color(button)
        size = self.manager.brush_size
        shape = self.manager.brush_shape
        
        pixels = self._get_brush_pixels(cx, cy, size, shape)
        
        for px, py in pixels:
            if not doc.in_bounds(px, py):
                continue
                
            current_color = layer.get_pixel(px, py)
            
            # Pikselin BOYANMADAN ÖNCEKİ rengini sadece bir kez kaydet
            if (px, py) not in self.before_pixels:
                self.before_pixels[(px, py)] = current_color if not current_color.is_transparent else None
                
            # Eğer zaten boyanacak renk aynıysa hiç işlem yapma (Performans)
            if current_color == color:
                continue
                
            self.after_pixels[(px, py)] = color
            
            # Anında görsel geribildirim (Core Update)
            if color is None:
                layer.set_pixel(px, py, Color(0, 0, 0, 0))
            else:
                layer.set_pixel(px, py, color)
                
            # Canvas'ı anında bilgilendir
            self.manager.update_canvas_pixel(px, py, color)
