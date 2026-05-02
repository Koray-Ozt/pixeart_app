from typing import List, Optional
from .layer import Layer

class Frame:
    """
    Represent a single animation frame containing multiple layers and a specific duration.
    """
    def __init__(self, duration_ms: int = 100):
        self.duration_ms = duration_ms
        self._layers: List[Layer] = []
        self._active_layer_index: int = -1

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

    def clone(self) -> "Frame":
        """Returns a deep copy of this frame, including cloned layers."""
        cloned_frame = Frame(duration_ms=self.duration_ms)
        for layer in self._layers:
            cloned_frame.add_layer(layer.clone(layer.name))
        cloned_frame._active_layer_index = self._active_layer_index
        return cloned_frame
