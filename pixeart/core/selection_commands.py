from typing import Dict, Tuple, Optional, List
from pixeart.core.history import Command
from pixeart.core.document import Document
from pixeart.core.color import Color


class MoveSelectionCommand(Command):
    def __init__(self, document: Document, layer_index: int,
                 pixels: Dict[Tuple[int, int], Optional[Color]],
                 dx: int, dy: int, name: str = "Move Selection"):
        self.document = document
        self.layer_index = layer_index
        self.pixels = pixels
        self.dx = dx
        self.dy = dy
        self.name = name

    def execute(self) -> None:
        if not (0 <= self.layer_index < len(self.document.layers)):
            return
        layer = self.document.layers[self.layer_index]
        # Eski konumdaki pikselleri sil
        for (x, y) in self.pixels:
            layer.set_pixel(x, y, Color(0, 0, 0, 0))
        # Yeni konuma yerleştir
        for (x, y), color in self.pixels.items():
            nx, ny = x + self.dx, y + self.dy
            if self.document.in_bounds(nx, ny) and color is not None:
                layer.set_pixel(nx, ny, color)
        self.document.is_dirty = True

    def undo(self) -> None:
        if not (0 <= self.layer_index < len(self.document.layers)):
            return
        layer = self.document.layers[self.layer_index]
        # Yeni konumdaki pikselleri sil
        for (x, y) in self.pixels:
            nx, ny = x + self.dx, y + self.dy
            if self.document.in_bounds(nx, ny):
                layer.set_pixel(nx, ny, Color(0, 0, 0, 0))
        # Eski konuma geri yerleştir
        for (x, y), color in self.pixels.items():
            if self.document.in_bounds(x, y) and color is not None:
                layer.set_pixel(x, y, color)
        self.document.is_dirty = True


class PasteCommand(Command):
    def __init__(self, document: Document, layer_index: int,
                 pixels: Dict[Tuple[int, int], Optional[Color]],
                 offset_x: int, offset_y: int, name: str = "Paste"):
        self.document = document
        self.layer_index = layer_index
        self.pixels = pixels
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.name = name
        self._overwritten: Dict[Tuple[int, int], Optional[Color]] = {}

    def execute(self) -> None:
        if not (0 <= self.layer_index < len(self.document.layers)):
            return
        layer = self.document.layers[self.layer_index]
        self._overwritten.clear()
        for (x, y), color in self.pixels.items():
            nx, ny = x + self.offset_x, y + self.offset_y
            if self.document.in_bounds(nx, ny):
                old = layer.get_pixel(nx, ny)
                self._overwritten[(nx, ny)] = old if not old.is_transparent else None
                if color is not None:
                    layer.set_pixel(nx, ny, color)
        self.document.is_dirty = True

    def undo(self) -> None:
        if not (0 <= self.layer_index < len(self.document.layers)):
            return
        layer = self.document.layers[self.layer_index]
        for (nx, ny), color in self._overwritten.items():
            if color is None:
                layer.set_pixel(nx, ny, Color(0, 0, 0, 0))
            else:
                layer.set_pixel(nx, ny, color)
        self.document.is_dirty = True


class DeleteSelectionCommand(Command):
    def __init__(self, document: Document, layer_index: int,
                 pixels: Dict[Tuple[int, int], Optional[Color]], name: str = "Delete"):
        self.document = document
        self.layer_index = layer_index
        self.pixels = pixels
        self.name = name

    def execute(self) -> None:
        if not (0 <= self.layer_index < len(self.document.layers)):
            return
        layer = self.document.layers[self.layer_index]
        for (x, y) in self.pixels:
            layer.set_pixel(x, y, Color(0, 0, 0, 0))
        self.document.is_dirty = True

    def undo(self) -> None:
        if not (0 <= self.layer_index < len(self.document.layers)):
            return
        layer = self.document.layers[self.layer_index]
        for (x, y), color in self.pixels.items():
            if color is not None:
                layer.set_pixel(x, y, color)
        self.document.is_dirty = True
