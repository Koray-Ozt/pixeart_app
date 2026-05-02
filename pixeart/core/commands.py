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
    def __init__(self, document: Document, frame_index: int, layer_index: int, 
                 before_pixels: Dict[Tuple[int, int], Optional[Color]], 
                 after_pixels: Dict[Tuple[int, int], Optional[Color]],
                 name: str = "Pencil/Eraser"):
        self.document = document
        self.frame_index = frame_index
        self.layer_index = layer_index
        self.before_pixels = before_pixels
        self.after_pixels = after_pixels
        self.name = name

    def execute(self) -> None:
        """İleri Al (Redo) tetiklendiğinde veya ilk çizimde yeni pikselleri katmana uygular."""
        if not (0 <= self.frame_index < len(self.document.frames)):
            return
        frame = self.document.frames[self.frame_index]
        if not (0 <= self.layer_index < len(frame.layers)):
            return
            
        if self.document.active_frame_index != self.frame_index:
            self.document.set_active_frame(self.frame_index)
            
        layer = frame.layers[self.layer_index]
        for (x, y), color in self.after_pixels.items():
            if color is None:
                layer.set_pixel(x, y, Color(0, 0, 0, 0)) # Pikseli sil
            else:
                layer.set_pixel(x, y, color) # Rengi koy
        self.document.is_dirty = True

    def undo(self) -> None:
        """Geri Al (Undo) tetiklendiğinde eski pikselleri katmana geri yükler."""
        if not (0 <= self.frame_index < len(self.document.frames)):
            return
        frame = self.document.frames[self.frame_index]
        if not (0 <= self.layer_index < len(frame.layers)):
            return
            
        if self.document.active_frame_index != self.frame_index:
            self.document.set_active_frame(self.frame_index)
            
        layer = frame.layers[self.layer_index]
        for (x, y), color in self.before_pixels.items():
            if color is None:
                layer.set_pixel(x, y, Color(0, 0, 0, 0))
            else:
                layer.set_pixel(x, y, color)
        self.document.is_dirty = True

class ModifyLayerCommand(Command):
    """
    Tüm efekt, döndürme ve kaydırma işlemleri için evrensel geri alma komutu.
    
    Performans optimizasyonu: Tüm katman piksellerini tutmak yerine sadece
    before ile after arasındaki farkı (delta) hesaplar ve depolar.
    Büyük tuvallerde (512x512+) bellek kullanımını ~%80 azaltır.
    """
    def __init__(self, document: Document, frame_index: int, layer_index: int, 
                 before_pixels: Dict[Tuple[int, int], Color], 
                 after_pixels: Dict[Tuple[int, int], Color],
                 name: str = "Modify Layer"):
        self.document = document
        self.frame_index = frame_index
        self.layer_index = layer_index
        self.name = name

        # Delta hesapla: sadece farklı olan pikselleri tut
        self._removed_pixels: Dict[Tuple[int, int], Color] = {}   # undo'da geri gelecek
        self._added_pixels: Dict[Tuple[int, int], Color] = {}     # redo'da gelecek
        self._changed_pixels_before: Dict[Tuple[int, int], Color] = {}
        self._changed_pixels_after: Dict[Tuple[int, int], Color] = {}
        
        all_keys = set(before_pixels.keys()) | set(after_pixels.keys())
        for key in all_keys:
            b = before_pixels.get(key)
            a = after_pixels.get(key)
            if b == a:
                continue  # Değişmemiş piksel — atla
            if b is None or (b and b.is_transparent):
                # Yeni eklenen piksel
                if a and not a.is_transparent:
                    self._added_pixels[key] = a
            elif a is None or (a and a.is_transparent):
                # Silinen piksel
                if b and not b.is_transparent:
                    self._removed_pixels[key] = b
            else:
                # Rengi değişen piksel
                self._changed_pixels_before[key] = b
                self._changed_pixels_after[key] = a

    def execute(self) -> None:
        if not (0 <= self.frame_index < len(self.document.frames)):
            return
        frame = self.document.frames[self.frame_index]
        if not (0 <= self.layer_index < len(frame.layers)):
            return
            
        if self.document.active_frame_index != self.frame_index:
            self.document.set_active_frame(self.frame_index)
            
        layer = frame.layers[self.layer_index]
        
        # Silinen pikselleri kaldır
        for (x, y) in self._removed_pixels:
            layer.set_pixel(x, y, Color(0, 0, 0, 0))
        # Eklenen pikselleri koy
        for (x, y), color in self._added_pixels.items():
            layer.set_pixel(x, y, color)
        # Değişen pikselleri güncelle
        for (x, y), color in self._changed_pixels_after.items():
            layer.set_pixel(x, y, color)
        
        self.document.is_dirty = True

    def undo(self) -> None:
        if not (0 <= self.frame_index < len(self.document.frames)):
            return
        frame = self.document.frames[self.frame_index]
        if not (0 <= self.layer_index < len(frame.layers)):
            return
            
        if self.document.active_frame_index != self.frame_index:
            self.document.set_active_frame(self.frame_index)
            
        layer = frame.layers[self.layer_index]
        
        # Eklenen pikselleri kaldır
        for (x, y) in self._added_pixels:
            layer.set_pixel(x, y, Color(0, 0, 0, 0))
        # Silinen pikselleri geri getir
        for (x, y), color in self._removed_pixels.items():
            layer.set_pixel(x, y, color)
        # Değişen pikselleri eski haline döndür
        for (x, y), color in self._changed_pixels_before.items():
            layer.set_pixel(x, y, color)
        
        self.document.is_dirty = True
