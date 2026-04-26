import math
import json
import logging
from typing import List, Optional, Tuple, Dict
from .layer import Layer
from .color import Color

logger = logging.getLogger(__name__)

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
    def get_flipped_horizontal(self, pixels: dict, bbox: Tuple[int, int, int, int] = None) -> dict:
        new_pixels = {}
        for (x, y), color in pixels.items():
            if bbox:
                nx = bbox[0] + bbox[2] - x
            else:
                nx = self._width - 1 - x
            new_pixels[(nx, y)] = color
        return new_pixels

    def get_flipped_vertical(self, pixels: dict, bbox: Tuple[int, int, int, int] = None) -> dict:
        new_pixels = {}
        for (x, y), color in pixels.items():
            if bbox:
                ny = bbox[1] + bbox[3] - y
            else:
                ny = self._height - 1 - y
            new_pixels[(x, ny)] = color
        return new_pixels

    def get_rotated(self, pixels: dict, angle: int, bbox: Tuple[int, int, int, int] = None) -> dict:
        angle = angle % 360
        new_pixels = {}
        if bbox:
            cx = (bbox[0] + bbox[2]) / 2.0
            cy = (bbox[1] + bbox[3]) / 2.0
        else:
            cx, cy = self._width / 2.0 - 0.5, self._height / 2.0 - 0.5
            
        for (x, y), color in pixels.items():
            nx, ny = x - cx, y - cy
            
            if angle == 90:
                rx, ry = -ny, nx
            elif angle == 180:
                rx, ry = -nx, -ny
            elif angle == 270:
                rx, ry = ny, -nx
            else:
                rx, ry = nx, ny
                
            final_x = int(round(rx + cx))
            final_y = int(round(ry + cy))
            
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

    def get_filled_pixels(self, base_pixels: dict, selection_mask: set, fill_color: "Color") -> dict:
        new_pixels = base_pixels.copy()
        if not selection_mask:
            for y in range(self.height):
                for x in range(self.width):
                    new_pixels[(x, y)] = fill_color
        else:
            for (x, y) in selection_mask:
                if self.in_bounds(x, y):
                    new_pixels[(x, y)] = fill_color
        return new_pixels

    def get_stroked_pixels(self, base_pixels: dict, selection_mask: set, stroke_color: "Color") -> dict:
        new_pixels = base_pixels.copy()
        if not selection_mask:
            return new_pixels
            
        dirs = [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)]
        stroke_pts = set()
        for (x, y) in selection_mask:
            is_edge = False
            for dx, dy in dirs:
                if (x + dx, y + dy) not in selection_mask:
                    is_edge = True
                    break
            if is_edge:
                stroke_pts.add((x, y))
                
        for (x, y) in stroke_pts:
            if self.in_bounds(x, y):
                new_pixels[(x, y)] = stroke_color
        return new_pixels

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self._width and 0 <= y < self._height

    def save_to_file(self, file_path: str) -> None:
        """
        Belgeyi .pixe (JSON) formatında diske yazar.
        Atomik yazma: önce geçici dosyaya yaz, başarılıysa yer değiştir.
        """
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
        
        import tempfile, os
        tmp_fd = None
        tmp_path = None
        try:
            dir_name = os.path.dirname(file_path) or "."
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pixe.tmp", dir=dir_name)
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                tmp_fd = None
                json.dump(data, f, ensure_ascii=False)
            os.replace(tmp_path, file_path)
            tmp_path = None
        except (OSError, IOError, TypeError, ValueError) as e:
            logger.error("Dosya kaydedilemedi: %s — %s", file_path, e)
            raise RuntimeError(f"Dosya kaydedilemedi: {e}") from e
        finally:
            if tmp_fd is not None:
                try:
                    os.close(tmp_fd)
                except OSError:
                    pass
            if tmp_path is not None:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        self.file_path = file_path
        self.is_dirty = False

    @classmethod
    def load_from_file(cls, file_path: str) -> "Document":
        """
        .pixe dosyasını okuyup Document nesnesi döndürür.
        Bozuk / eksik verili dosyalarda anlaşılır hata fırlatır.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Dosya bozuk (JSON hatası): {e}") from e
        except (OSError, IOError) as e:
            raise RuntimeError(f"Dosya okunamadı: {e}") from e
        
        if not isinstance(data, dict):
            raise RuntimeError("Dosya formatı geçersiz: kök öğe dict olmalı.")
        for key in ("width", "height"):
            if key not in data or not isinstance(data[key], int) or data[key] <= 0:
                raise RuntimeError(f"Dosya formatı geçersiz: '{key}' eksik veya hatalı.")
        
        try:
            doc = cls(data["width"], data["height"])
            doc._active_layer_index = data.get("active_layer_index", 0)
            
            for layer_data in data.get("layers", []):
                layer = Layer(layer_data.get("name", "Katman"))
                layer.is_visible = layer_data.get("is_visible", True)
                layer.is_locked = layer_data.get("is_locked", False)
                layer.opacity = layer_data.get("opacity", 1.0)
                layer.blend_mode = layer_data.get("blend_mode", "Normal")
                
                for p in layer_data.get("pixels", []):
                    layer.set_pixel(p["x"], p["y"], Color(p["r"], p["g"], p["b"], p.get("a", 255)))
                    
                doc.add_layer(layer)
                
            doc._active_layer_index = data.get("active_layer_index", 0)
                
            doc.file_path = file_path
            doc.is_dirty = False
            return doc
        except (KeyError, TypeError, ValueError) as e:
            raise RuntimeError(f"Dosya verileri bozuk: {e}") from e
