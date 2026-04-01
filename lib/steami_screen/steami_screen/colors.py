"""
Color conversion utilities for STeaMi display backends.

Colors are represented as RGB tuples (r, g, b) with values 0-255.
Each backend converts to its native format:
  - SSD1327 : grayscale 4-bit (0-15)
  - GC9A01  : RGB565 (16-bit)
  - Simulator: RGB tuple (pass-through)

All functions accept legacy int values for backward compatibility.
"""


def rgb_to_gray4(color):
    """Convert an RGB tuple to a 4-bit grayscale value (0-15).

    Uses BT.601 luminance: Y = 0.299*R + 0.587*G + 0.114*B
    Accepts int for backward compatibility (returned as-is, clamped to 0-15).
    """
    if isinstance(color, int):
        return max(0, min(15, color))
    r, g, b = color
    luminance = (r * 77 + g * 150 + b * 29) >> 8  # 0-255
    return luminance >> 4  # 0-15


def rgb_to_rgb565(color):
    """Convert an RGB tuple to a 16-bit RGB565 integer.

    Accepts int for backward compatibility (treated as gray4, expanded).
    """
    if isinstance(color, int):
        g = max(0, min(15, color)) * 17  # 0-255
        r, b = g, g
    else:
        r, g, b = color
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def rgb_to_rgb8(color):
    """Convert a color to an RGB tuple (r, g, b).

    If already a tuple, returns it unchanged.
    Accepts int for backward compatibility (treated as gray4, expanded).
    """
    if isinstance(color, int):
        v = max(0, min(15, color)) * 17  # 0-255
        return (v, v, v)
    return color
