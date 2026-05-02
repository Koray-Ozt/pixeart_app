from pixeart.core.color import Color

def test_color_system():
    # 1. Base conversion
    red = Color(255, 0, 0)
    h, s, v = red.to_hsv()
    print(f"Red HSV: {h}, {s}, {v}")
    
    red_back = Color.from_hsv(h, s, v)
    print(f"Red Back: {red_back.r}, {red_back.g}, {red_back.b}")
    
    # 2. Ramp
    print("\nColor Ramp (Blue):")
    blue = Color(0, 0, 255)
    ramp = blue.get_ramp(3, 3)
    for i, c in enumerate(ramp):
        print(f"Step {i}: {c.to_hex()} (L: {c.luminance:.2f})")
        
    # 3. Harmonies
    print("\nGreen Harmonies:")
    green = Color(0, 255, 0)
    harms = green.get_harmonies()
    for name, colors in harms.items():
        print(f"{name}: {[c.to_hex() for c in colors]}")
