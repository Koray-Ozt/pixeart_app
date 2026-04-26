from typing import Dict, Tuple, Optional
from pixeart.core.history import Command
from pixeart.core.document import Document
from pixeart.core.color import Color

class DrawCommand(Command):
    """
    Kalem veya Silgi gibi araçlarla yapılan boyama işlemlerinin
    öncesini ve sonrasını kaydederek Geri Al (Undo) / İleri Al (Redo) 
    işlemlerine olanak tanıyan komut sınıfı.
    """
    def __init__(self, document: Document, layer_index: int, 
                 before_pixels: Dict[Tuple[int, int], Optional[Color]], 
                 after_pixels: Dict[Tuple[int, int], Optional[Color]],
                 name: str = "Pencil/Eraser"):
        self.document = document
        self.layer_index = layer_index
        self.before_pixels = before_pixels
        self.after_pixels = after_pixels
        self.name = name

    def execute(self) -> None:
        """İleri Al (Redo) tetiklendiğinde veya ilk çizimde yeni pikselleri katmana uygular."""
        if not (0 <= self.layer_index < len(self.document.layers)):
            return
            
        layer = self.document.layers[self.layer_index]
        for (x, y), color in self.after_pixels.items():
            if color is None:
                layer.set_pixel(x, y, Color(0, 0, 0, 0)) # Pikseli sil
            else:
                layer.set_pixel(x, y, color) # Rengi koy
        self.document.is_dirty = True

    def undo(self) -> None:
        """Geri Al (Undo) tetiklendiğinde eski pikselleri katmana geri yükler."""
        if not (0 <= self.layer_index < len(self.document.layers)):
            return
            
        layer = self.document.layers[self.layer_index]
        for (x, y), color in self.before_pixels.items():
            if color is None:
                layer.set_pixel(x, y, Color(0, 0, 0, 0))
            else:
                layer.set_pixel(x, y, color)
        self.document.is_dirty = True

class ModifyLayerCommand(Command):
    """
    Tüm efekt, döndürme ve kaydırma işlemleri için evrensel geri alma komutu.
    İşlem öncesi ve sonrası tüm katman piksellerini tutar.
    """
    def __init__(self, document: Document, layer_index: int, 
                 before_pixels: Dict[Tuple[int, int], Color], 
                 after_pixels: Dict[Tuple[int, int], Color],
                 name: str = "Modify Layer"):
        self.document = document
        self.layer_index = layer_index
        self.before_pixels = before_pixels
        self.after_pixels = after_pixels
        self.name = name

    def execute(self) -> None:
        if not (0 <= self.layer_index < len(self.document.layers)):
            return
            
        layer = self.document.layers[self.layer_index]
        layer.clear()
        
        for (x, y), color in self.after_pixels.items():
            if not color.is_transparent:
                layer.set_pixel(x, y, color)
        self.document.is_dirty = True

    def undo(self) -> None:
        if not (0 <= self.layer_index < len(self.document.layers)):
            return
            
        layer = self.document.layers[self.layer_index]
        layer.clear()
        
        for (x, y), color in self.before_pixels.items():
            if not color.is_transparent:
                layer.set_pixel(x, y, color)
        self.document.is_dirty = True
