from typing import Dict, Tuple, Optional
from .color import Color

class Layer:
    def __init__(self, name: str):
        self.name = name
        self.is_visible: bool = True
        self.is_locked: bool = False
        self.opacity: float = 1.0
        self._pixels: Dict[Tuple[int, int], Color] = {}
        self._bbox: Optional[Tuple[int, int, int, int]] = None
        self._bbox_dirty: bool = False

    def get_pixel(self, x: int, y: int) -> Color:
        return self._pixels.get((x, y), Color(0, 0, 0, 0))

    def set_pixel(self, x: int, y: int, color: Color) -> None:
        if self.is_locked:
            return
            
        if color.is_transparent:
            if (x, y) in self._pixels:
                del self._pixels[(x, y)]
                self._bbox_dirty = True
        else:
            self._pixels[(x, y)] = color
            
            if self._bbox is not None and not self._bbox_dirty:
                min_x, min_y, max_x, max_y = self._bbox
                if x < min_x or x > max_x or y < min_y or y > max_y:
                    self._bbox = (min(min_x, x), min(min_y, y), max(max_x, x), max(max_y, y))
            else:
                self._bbox_dirty = True

    def clear(self) -> None:
        if not self.is_locked:
            self._pixels.clear()
            self._bbox = None
            self._bbox_dirty = False

    @property
    def bounding_box(self) -> Optional[Tuple[int, int, int, int]]:
        if not self._pixels:
            return None
            
        if self._bbox_dirty or self._bbox is None:
            xs = [p[0] for p in self._pixels.keys()]
            ys = [p[1] for p in self._pixels.keys()]
            self._bbox = (min(xs), min(ys), max(xs), max(ys))
            self._bbox_dirty = False
            
        return self._bbox

    @property
    def active_pixels(self) -> Dict[Tuple[int, int], Color]:
        return self._pixels.copy()
        
    def get_blended_pixel(self, x: int, y: int) -> Color:
        color = self.get_pixel(x, y)
        if self.opacity < 1.0 and not color.is_transparent:
            return Color(color.r, color.g, color.b, int(color.a * self.opacity))
        return color

    def clone(self, new_name: Optional[str] = None) -> "Layer":
        cloned = Layer(name=new_name or f"{self.name} (Kopya)")
        cloned.is_visible = self.is_visible
        cloned.is_locked = self.is_locked
        cloned.opacity = self.opacity
        cloned._pixels = self._pixels.copy()
        cloned._bbox = self._bbox
        cloned._bbox_dirty = self._bbox_dirty
        return cloned
