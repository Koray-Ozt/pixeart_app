from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class Color:
    r: int
    g: int
    b: int
    a: int = 255

    @classmethod
    def from_hex(cls, hex_color: str) -> "Color":
        hex_str = hex_color.lstrip('#')
        if len(hex_str) == 6:
            r, g, b = (int(hex_str[i:i+2], 16) for i in (0, 2, 4))
            return cls(r, g, b, 255)
        elif len(hex_str) == 8:
            r, g, b, a = (int(hex_str[i:i+2], 16) for i in (0, 2, 4, 6))
            return cls(r, g, b, a)
        raise ValueError(f"Invalid hex format: {hex_color}")

    def to_hex(self, include_alpha: bool = False) -> str:
        if include_alpha:
            return f"#{self.r:02X}{self.g:02X}{self.b:02X}{self.a:02X}"
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}"

    def to_rgba_tuple(self) -> Tuple[int, int, int, int]:
        return (self.r, self.g, self.b, self.a)

    def to_rgb_tuple(self) -> Tuple[int, int, int]:
        return (self.r, self.g, self.b)
    
    @property
    def is_transparent(self) -> bool:
        return self.a == 0

    def blend_with(self, background: "Color") -> "Color":
        if self.a == 255:
            return self
        if self.a == 0:
            return background
            
        alpha_src = self.a / 255.0
        alpha_bg = background.a / 255.0
        
        out_alpha = alpha_src + alpha_bg * (1 - alpha_src)
        if out_alpha == 0:
            return Color(0, 0, 0, 0)
            
        r = int((self.r * alpha_src + background.r * alpha_bg * (1 - alpha_src)) / out_alpha)
        g = int((self.g * alpha_src + background.g * alpha_bg * (1 - alpha_src)) / out_alpha)
        b = int((self.b * alpha_src + background.b * alpha_bg * (1 - alpha_src)) / out_alpha)
        a = int(out_alpha * 255)
        
        return Color(r, g, b, a)
