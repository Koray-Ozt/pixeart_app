import math
from typing import List, Optional
from .layer import Layer

class Document:
    def __init__(self, width: int, height: int):
        if width <= 0 or height <= 0:
            raise ValueError("Width and height must be > 0.")
            
        self._width = width
        self._height = height
        self._layers: List[Layer] = []  
        self._active_layer_index: int = -1
        self.file_path: Optional[str] = None
        self.is_dirty: bool = False

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height
        
    @property
    def layers(self) -> List[Layer]:
        return list(self._layers)

    @property
    def active_layer_index(self) -> int:
        return self._active_layer_index

    @property
    def active_layer(self) -> Optional[Layer]:
        if 0 <= self._active_layer_index < len(self._layers):
            return self._layers[self._active_layer_index]
        return None

    def add_layer(self, layer: Layer, index: Optional[int] = None) -> None:
        if index is None:
            self._layers.append(layer)
            self._active_layer_index = len(self._layers) - 1
        else:
            self._layers.insert(index, layer)
            self._active_layer_index = index
        self.is_dirty = True

    def remove_layer(self, index: int) -> None:
        if not (0 <= index < len(self._layers)):
            raise IndexError("Invalid layer index.")
            
        del self._layers[index]
        
        if not self._layers:
            self._active_layer_index = -1
        elif self._active_layer_index > index:
            self._active_layer_index -= 1
        elif self._active_layer_index == index:
            self._active_layer_index = min(index, len(self._layers) - 1)
            
        self.is_dirty = True

    def set_active_layer(self, index: int) -> None:
        if 0 <= index < len(self._layers):
            self._active_layer_index = index
        else:
            raise IndexError("Invalid layer index.")

    def reorder_layer(self, source_index: int, dest_index: int) -> None:
        if 0 <= source_index < len(self._layers) and 0 <= dest_index < len(self._layers):
            layer = self._layers.pop(source_index)
            self._layers.insert(dest_index, layer)
            if self._active_layer_index == source_index:
                self._active_layer_index = dest_index
            elif source_index < self._active_layer_index <= dest_index:
                self._active_layer_index -= 1
            elif dest_index <= self._active_layer_index < source_index:
                self._active_layer_index += 1
            self.is_dirty = True

    # --- Dönüşüm ve Kaydırma (Transform & Shift) ---
    def get_flipped_horizontal(self, pixels: dict) -> dict:
        new_pixels = {}
        for (x, y), color in pixels.items():
            new_pixels[(self._width - 1 - x, y)] = color
        return new_pixels

    def get_flipped_vertical(self, pixels: dict) -> dict:
        new_pixels = {}
        for (x, y), color in pixels.items():
            new_pixels[(x, self._height - 1 - y)] = color
        return new_pixels

    def get_rotated(self, pixels: dict, angle: int) -> dict:
        # Sadece 90, 180, -90 (-90 = 270) desteklenir
        angle = angle % 360
        new_pixels = {}
        cx, cy = self._width / 2.0, self._height / 2.0
        
        for (x, y), color in pixels.items():
            # Merkeze göre ötele
            nx, ny = x - cx + 0.5, y - cy + 0.5
            
            # Döndür
            if angle == 90:
                rx, ry = -ny, nx
            elif angle == 180:
                rx, ry = -nx, -ny
            elif angle == 270:
                rx, ry = ny, -nx
            else:
                rx, ry = nx, ny
                
            # Geri ötele
            final_x, final_y = int(math.floor(rx + cx - 0.5)), int(math.floor(ry + cy - 0.5))
            
            # Tuval içinde kalanları al
            if self.in_bounds(final_x, final_y):
                new_pixels[(final_x, final_y)] = color
                
        return new_pixels

    def get_shifted(self, pixels: dict, dx: int, dy: int) -> dict:
        new_pixels = {}
        for (x, y), color in pixels.items():
            nx = (x + dx) % self._width
            ny = (y + dy) % self._height
            new_pixels[(nx, ny)] = color
        return new_pixels

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self._width and 0 <= y < self._height

    def save_to_file(self, file_path: str) -> None:
        data = {
            "version": 1,
            "width": self._width,
            "height": self._height,
            "active_layer_index": self._active_layer_index,
            "layers": []
        }
        for layer in self._layers:
            layer_data = {
                "name": layer.name,
                "is_visible": layer.is_visible,
                "is_locked": layer.is_locked,
                "opacity": layer.opacity,
                "blend_mode": getattr(layer, "blend_mode", "Normal"),
                "pixels": []
            }
            for (x, y), color in layer.active_pixels.items():
                layer_data["pixels"].append({
                    "x": x, "y": y,
                    "r": color.r, "g": color.g, "b": color.b, "a": color.a
                })
            data["layers"].append(layer_data)
            
        import json
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
            
        self.file_path = file_path
        self.is_dirty = False

    @classmethod
    def load_from_file(cls, file_path: str) -> "Document":
        import json
        from .color import Color
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        doc = cls(data["width"], data["height"])
        doc._active_layer_index = data.get("active_layer_index", 0)
        
        for layer_data in data.get("layers", []):
            layer = Layer(layer_data["name"])
            layer.is_visible = layer_data.get("is_visible", True)
            layer.is_locked = layer_data.get("is_locked", False)
            layer.opacity = layer_data.get("opacity", 1.0)
            layer.blend_mode = layer_data.get("blend_mode", "Normal")
            
            for p in layer_data.get("pixels", []):
                layer.set_pixel(p["x"], p["y"], Color(p["r"], p["g"], p["b"], p.get("a", 255)))
                
            doc.add_layer(layer)
            
        # Eğer add_layer active_layer_index'i değiştiriyorsa geri düzeltelim
        doc._active_layer_index = data.get("active_layer_index", 0)
            
        doc.file_path = file_path
        doc.is_dirty = False
        return doc
