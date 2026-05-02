import math
import colorsys
from dataclasses import dataclass
from typing import Tuple, List, Dict, Optional

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

    @property
    def luminance(self) -> float:
        """Algılanan parlaklık (Perceived Luminance)."""
        return (0.299 * self.r + 0.587 * self.g + 0.114 * self.b) / 255.0

    # --- HSV Dönüşümleri ---
    def to_hsv(self) -> Tuple[float, float, float]:
        """(H [0-1], S [0-1], V [0-1]) döner."""
        return colorsys.rgb_to_hsv(self.r / 255.0, self.g / 255.0, self.b / 255.0)

    @classmethod
    def from_hsv(cls, h: float, s: float, v: float, a: int = 255) -> "Color":
        rgb = colorsys.hsv_to_rgb(h, s, v)
        return cls(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255), a)

    # --- Renk Matematiği ---
    def distance_to(self, other: "Color") -> float:
        """Euclidean mesafe (RGB uzayında)."""
        return math.sqrt((self.r - other.r)**2 + (self.g - other.g)**2 + (self.b - other.b)**2)

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

    # --- Profesyonel Renk Rampası (Hue Shifting) ---
    def get_ramp(self, light_steps: int = 3, shadow_steps: int = 3) -> List["Color"]:
        """
        Profesyonel hue-shifting algoritması ile renk rampası üretir.
        Işıklar: V artar, S azalır, H sarıya (60 deg) kayar.
        Gölgeler: V azalır, S artar, H maviye (240 deg) kayar.
        """
        h, s, v = self.to_hsv()
        ramp = []

        # Gölgeler
        for i in range(shadow_steps, 0, -1):
            step = i / (shadow_steps + 1)
            # Hue shift towards 240 (Blue/Purple)
            new_h = self._shift_hue(h, 0.66, step * 0.1)
            new_s = min(1.0, s + step * 0.2)
            new_v = max(0.0, v - step * 0.4)
            ramp.append(Color.from_hsv(new_h, new_s, new_v))

        # Ana Renk
        ramp.append(self)

        # Işıklar
        for i in range(1, light_steps + 1):
            step = i / (light_steps + 1)
            # Hue shift towards 60 (Yellow)
            new_h = self._shift_hue(h, 0.16, step * 0.1)
            new_s = max(0.0, s - step * 0.2)
            new_v = min(1.0, v + step * 0.4)
            ramp.append(Color.from_hsv(new_h, new_s, new_v))

        return ramp

    def get_harmonies(self) -> Dict[str, List["Color"]]:
        """Renk teorisi uyumlarını döner."""
        h, s, v = self.to_hsv()
        return {
            "complementary": [Color.from_hsv((h + 0.5) % 1.0, s, v)],
            "analogous": [Color.from_hsv((h - 0.083) % 1.0, s, v), Color.from_hsv((h + 0.083) % 1.0, s, v)],
            "triadic": [Color.from_hsv((h + 0.333) % 1.0, s, v), Color.from_hsv((h + 0.666) % 1.0, s, v)]
        }

    def _shift_hue(self, h: float, target_h: float, amount: float) -> float:
        """H değerini hedef H değerine doğru belirli bir miktarda kaydırır."""
        diff = target_h - h
        if diff > 0.5: diff -= 1.0
        if diff < -0.5: diff += 1.0
        return (h + diff * amount) % 1.0

def color_distance(c1: Color, c2: Color) -> float:
    """Kırmızı-ortalama (Redmean) yaklaşımı (Geriye dönük uyumluluk için)."""
    rmean = (c1.r + c2.r) / 2.0
    r = c1.r - c2.r
    g = c1.g - c2.g
    b = c1.b - c2.b
    return math.sqrt((2 + rmean/256.0)*(r**2) + 4*(g**2) + (2 + (255-rmean)/256.0)*(b**2))
