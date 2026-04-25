from typing import Dict, Tuple, Optional
from PyQt6.QtCore import Qt
from pixeart.core.color import Color
from .pencil import PencilTool

class EraserTool(PencilTool):
    """
    Silgi Aracı (Eraser Tool)
    Kalem ile mimarisi tamamen aynıdır. Tek farkı, boyadığı rengin "None" 
    (Saydam/Transparent) olmasıdır. Bu yüzden kod tekrarı yapmamak adına
    doğrudan PencilTool'dan miras alır ve sadece fırça vurma metodunu ezer.
    """
    
    def _apply_brush(self, cx: int, cy: int, button: int) -> None:
        doc = self.manager.document
        layer_idx = doc.active_layer_index
        if layer_idx < 0 or layer_idx >= len(doc.layers):
            return
            
        layer = doc.layers[layer_idx]
        if not layer.is_visible or layer.is_locked:
            return 
            
        # SİLGİNİN FARKI: Renk her zaman 'None' (Yani Saydamlık/Silme)
        color = None 
        size = self.manager.brush_size
        shape = self.manager.brush_shape
        
        pixels = self._get_brush_pixels(cx, cy, size, shape)
        
        for px, py in pixels:
            if not doc.in_bounds(px, py):
                continue
                
            current_color = layer.get_pixel(px, py)
            
            if (px, py) not in self.before_pixels:
                self.before_pixels[(px, py)] = current_color if not current_color.is_transparent else None
                
            if current_color.is_transparent:
                continue
                
            self.after_pixels[(px, py)] = color
            
            # Silgi olduğu için rengi kaldırırız
            layer.set_pixel(px, py, Color(0, 0, 0, 0))
            self.manager.update_canvas_pixel(px, py, None)
