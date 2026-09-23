"""Constants for the steami_screen module."""

from micropython import const

# --- Color constants (RGB tuples) ---
# Grays map to exact SSD1327 levels: gray4 * 17 gives R=G=B
BLACK = (0, 0, 0)
DARK = (102, 102, 102)  # gray4=6
GRAY = (153, 153, 153)  # gray4=9
LIGHT = (187, 187, 187)  # gray4=11
WHITE = (255, 255, 255)  # gray4=15

# Accent colors (used on color displays, degrade gracefully to gray on SSD1327)
GREEN = (119, 255, 119)
RED = (255, 85, 85)
BLUE = (85, 85, 255)
YELLOW = (255, 255, 85)

# Internal grid color (used by graph widget)
GRID_DARK = (51, 51, 51)

# --- Pixel-art face bitmaps (8x8, MSB = left) ---
FACES = {
    "happy": (0x00, 0x24, 0x24, 0x00, 0x00, 0x42, 0x3C, 0x00),
    "sad": (0x00, 0x24, 0x24, 0x00, 0x00, 0x3C, 0x42, 0x00),
    "surprised": (0x00, 0x24, 0x24, 0x00, 0x18, 0x24, 0x24, 0x18),
    "sleeping": (0x00, 0x00, 0x66, 0x00, 0x00, 0x18, 0x18, 0x00),
    "angry": (0x00, 0x42, 0x24, 0x24, 0x00, 0x3C, 0x42, 0x00),
    "love": (0x00, 0x66, 0xFF, 0xFF, 0x7E, 0x3C, 0x18, 0x00),
}

# --- Framebuf built-in font dimensions ---
STEAMI_CHAR_W = const(8)
STEAMI_CHAR_H = const(8)

# --- Default screen dimensions (SSD1327) ---
STEAMI_DEFAULT_WIDTH = const(128)
STEAMI_DEFAULT_HEIGHT = const(128)

# --- Gauge widget ---
STEAMI_GAUGE_START_ANGLE = const(135)
STEAMI_GAUGE_SWEEP = const(270)

# --- Graph widget layout ---
STEAMI_GRAPH_MARGIN = const(15)
STEAMI_GRAPH_X_OFFSET = const(6)
STEAMI_GRAPH_Y = const(38)
STEAMI_GRAPH_HEIGHT = const(52)
STEAMI_GRAPH_VALUE_Y = const(31)
STEAMI_GRAPH_DASH = const(3)
STEAMI_GRAPH_GAP = const(3)
