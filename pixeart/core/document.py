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

    def move_layer_up(self, index: int) -> None:
        if 0 <= index < len(self._layers) - 1:
            self._layers[index], self._layers[index+1] = self._layers[index+1], self._layers[index]
            if self._active_layer_index == index:
                self._active_layer_index += 1
            elif self._active_layer_index == index + 1:
                self._active_layer_index -= 1
            self.is_dirty = True

    def move_layer_down(self, index: int) -> None:
        if 0 < index < len(self._layers):
            self._layers[index], self._layers[index-1] = self._layers[index-1], self._layers[index]
            if self._active_layer_index == index:
                self._active_layer_index -= 1
            elif self._active_layer_index == index - 1:
                self._active_layer_index += 1
            self.is_dirty = True

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self._width and 0 <= y < self._height
