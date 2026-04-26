import colorsys
import math
from typing import Dict, Tuple, List, Callable
from pixeart.core.color import Color

def _map_pixels(pixels: Dict[Tuple[int, int], Color], func: Callable[[Color], Color]) -> Dict[Tuple[int, int], Color]:
    new_pixels = {}
    for (x, y), color in pixels.items():
        if color.is_transparent:
            new_pixels[(x, y)] = color
        else:
            new_pixels[(x, y)] = func(color)
    return new_pixels

def invert_colors(pixels: Dict[Tuple[int, int], Color]) -> Dict[Tuple[int, int], Color]:
    def invert(c: Color) -> Color:
        return Color(255 - c.r, 255 - c.g, 255 - c.b, c.a)
    return _map_pixels(pixels, invert)

def grayscale(pixels: Dict[Tuple[int, int], Color]) -> Dict[Tuple[int, int], Color]:
    def gray(c: Color) -> Color:
        # Luma formula
        v = int(c.r * 0.299 + c.g * 0.587 + c.b * 0.114)
        return Color(v, v, v, c.a)
    return _map_pixels(pixels, gray)

def adjust_brightness_contrast(pixels: Dict[Tuple[int, int], Color], brightness: int, contrast: int) -> Dict[Tuple[int, int], Color]:
    # brightness: -100 to 100, contrast: -100 to 100
    factor = (259 * (contrast + 255)) / (255 * (259 - contrast))
    
    def adjust(c: Color) -> Color:
        def clamp(val):
            return max(0, min(255, int(val)))
            
        r = clamp(factor * (c.r - 128) + 128 + brightness)
        g = clamp(factor * (c.g - 128) + 128 + brightness)
        b = clamp(factor * (c.b - 128) + 128 + brightness)
        return Color(r, g, b, c.a)
    return _map_pixels(pixels, adjust)

def replace_color(pixels: Dict[Tuple[int, int], Color], target: Color, new_color: Color, tolerance: int = 0) -> Dict[Tuple[int, int], Color]:
    def color_dist(c1, c2):
        return math.sqrt((c1.r - c2.r)**2 + (c1.g - c2.g)**2 + (c1.b - c2.b)**2 + (c1.a - c2.a)**2)

    def replace(c: Color) -> Color:
        if tolerance == 0:
            return new_color if c == target else c
        if color_dist(c, target) <= tolerance:
            return new_color
        return c
    return _map_pixels(pixels, replace)

def adjust_hue_saturation(pixels: Dict[Tuple[int, int], Color], hue_shift: int, sat_shift: int, lightness_shift: int) -> Dict[Tuple[int, int], Color]:
    # hue: -180 to 180, sat: -100 to 100, lightness: -100 to 100
    def adjust(c: Color) -> Color:
        h, l, s = colorsys.rgb_to_hls(c.r / 255.0, c.g / 255.0, c.b / 255.0)
        
        # Adjust hue
        h = (h + (hue_shift / 360.0)) % 1.0
        if h < 0: h += 1.0
        
        # Adjust saturation
        if sat_shift > 0:
            s += (1.0 - s) * (sat_shift / 100.0)
        else:
            s += s * (sat_shift / 100.0)
            
        # Adjust lightness
        if lightness_shift > 0:
            l += (1.0 - l) * (lightness_shift / 100.0)
        else:
            l += l * (lightness_shift / 100.0)
            
        s = max(0.0, min(1.0, s))
        l = max(0.0, min(1.0, l))
        
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return Color(int(r * 255), int(g * 255), int(b * 255), c.a)
    return _map_pixels(pixels, adjust)

def apply_color_curve(pixels: Dict[Tuple[int, int], Color], curve_points: List[Tuple[int, int]]) -> Dict[Tuple[int, int], Color]:
    # A simple linear interpolation lookup table based on curve points
    if not curve_points:
        return pixels.copy()
        
    pts = sorted(curve_points, key=lambda p: p[0])
    lut = [0] * 256
    
    idx = 0
    for i in range(256):
        if i <= pts[0][0]:
            lut[i] = pts[0][1]
        elif i >= pts[-1][0]:
            lut[i] = pts[-1][1]
        else:
            while idx < len(pts) - 1 and pts[idx+1][0] < i:
                idx += 1
            x0, y0 = pts[idx]
            x1, y1 = pts[idx+1]
            ratio = (i - x0) / (x1 - x0) if x1 != x0 else 0
            lut[i] = int(y0 + ratio * (y1 - y0))
            lut[i] = max(0, min(255, lut[i]))

    def apply_curve(c: Color) -> Color:
        return Color(lut[c.r], lut[c.g], lut[c.b], c.a)
    return _map_pixels(pixels, apply_curve)

def apply_outline(pixels: Dict[Tuple[int, int], Color], outline_color: Color) -> Dict[Tuple[int, int], Color]:
    new_pixels = pixels.copy()
    
    # 4-way neighbors
    dirs = [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)]
    
    to_add = {}
    for (x, y), color in pixels.items():
        if color.is_transparent:
            continue
            
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            if (nx, ny) not in pixels or pixels[(nx, ny)].is_transparent:
                to_add[(nx, ny)] = outline_color
                
    for pos, color in to_add.items():
        if pos not in new_pixels or new_pixels[pos].is_transparent:
            new_pixels[pos] = color
            
    return new_pixels

def apply_convolution_matrix(pixels: Dict[Tuple[int, int], Color], matrix: List[List[float]], width: int, height: int) -> Dict[Tuple[int, int], Color]:
    # matrix is 3x3
    new_pixels = {}
    
    for (x, y), color in pixels.items():
        if color.is_transparent:
            new_pixels[(x, y)] = color
            continue
            
        r_sum, g_sum, b_sum = 0.0, 0.0, 0.0
        
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                nx, ny = x + dx, y + dy
                weight = matrix[dy+1][dx+1]
                
                # If out of bounds or empty, assume transparent/black (0)
                if 0 <= nx < width and 0 <= ny < height and (nx, ny) in pixels:
                    c = pixels[(nx, ny)]
                    if not c.is_transparent:
                        r_sum += c.r * weight
                        g_sum += c.g * weight
                        b_sum += c.b * weight
                        
        def clamp(v): return max(0, min(255, int(v)))
        new_pixels[(x, y)] = Color(clamp(r_sum), clamp(g_sum), clamp(b_sum), color.a)
        
    return new_pixels
