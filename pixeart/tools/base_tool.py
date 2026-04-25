from enum import Enum, auto
from typing import List, Tuple, Set
from PyQt6.QtCore import Qt

class BrushShape(Enum):
    SQUARE = auto()
    CIRCLE = auto()

class BaseTool:
    """
    Tüm çizim araçlarının (Kalem, Silgi, Boya Kovası) türetileceği soyut taban sınıfı.
    Araçların temel özellikleri (Mouse Click, Drag, Release) ve fırça matematiklerini barındırır.
    """
    def __init__(self):
        self.manager = None # ToolManager tarafından çalışma zamanında (runtime) atanır.
        
    def on_press(self, x: int, y: int, button: Qt.MouseButton) -> None:
        pass
        
    def on_drag(self, x: int, y: int, button: Qt.MouseButton) -> None:
        pass
        
    def on_release(self, x: int, y: int, button: Qt.MouseButton) -> None:
        pass
        
    def _get_brush_pixels(self, cx: int, cy: int, size: int, shape: BrushShape) -> List[Tuple[int, int]]:
        """
        Verilen merkez (cx, cy) koordinatında, belirtilen kalınlık ve şekle göre
        boyanması gereken tüm piksellerin listesini döner.
        """
        pixels = set()
        
        # 1 piksel kalınlık için karmaşık matematiğe gerek yok
        if size == 1:
            return [(cx, cy)]
            
        r = size // 2
        
        if shape == BrushShape.SQUARE:
            # Boyut çift sayıysa merkez noktası hafif sağ-alta kayar (Standart pixel art kuralı)
            start_x = cx - r if size % 2 != 0 else cx - r + 1
            start_y = cy - r if size % 2 != 0 else cy - r + 1
            
            for i in range(size):
                for j in range(size):
                    pixels.add((start_x + i, start_y + j))
                    
        elif shape == BrushShape.CIRCLE:
            # Dairesel fırça için Euclidean mesafe hesaplaması
            r_sq = (size / 2.0) ** 2
            start_x = cx - r if size % 2 != 0 else cx - r + 1
            start_y = cy - r if size % 2 != 0 else cy - r + 1
            
            # Pürüzsüz bir daire için merkez offset düzeltmesi
            center_x = cx if size % 2 != 0 else cx + 0.5
            center_y = cy if size % 2 != 0 else cy + 0.5
            
            for i in range(size):
                for j in range(size):
                    px = start_x + i
                    py = start_y + j
                    dist_sq = (px - center_x)**2 + (py - center_y)**2
                    if dist_sq <= r_sq:
                        pixels.add((px, py))
                        
        return list(pixels)
        
    def _interpolate_line(self, x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
        """
        Bresenham's Line Algoritması
        Kullanıcı fareyi çok hızlı sürüklediğinde (Drag) iki nokta arasında
        kalan boşlukları (Gap) doldurmak için matematiksel interpolasyon yapar.
        """
        pixels = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        while True:
            pixels.append((x0, y0))
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
                
        return pixels
