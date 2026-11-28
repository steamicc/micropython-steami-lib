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

# Internal grid color (graph middle line, bar track)
GRID_DARK = (51, 51, 51)

# Grey minimum contrast (Arduino STEAMI_MIN_CONTRAST): on a grey panel, a
# widget foreground over the widget's own background is at least this many
# grey4 levels above it (BLUE and DARK are both grey4 6).
STEAMI_MIN_CONTRAST = const(4)

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

# --- Round-screen fitting (k > 1), in 128 px cells or units ---
# A title row is lowered for at most a 13-cell text: the N/S row cap.
STEAMI_TITLE_CAP_CELLS = const(13)
# value(): gap between a W/E half region and the centre; what CENTER, N and S
# keep off the available width.
STEAMI_VALUE_SIDE_GAP = const(3)
STEAMI_VALUE_FIT_MARGIN = const(4)
# value(): gap between the label cell (12 px tall on 240) and the value top.
STEAMI_VALUE_LABEL_GAP = const(4)
# menu(): a row is shown when the chord at its cells holds this many cells.
STEAMI_MENU_ROW_CELLS = const(12)

# --- Gauge widget ---
STEAMI_GAUGE_START_ANGLE = const(135)
STEAMI_GAUGE_SWEEP = const(270)
# When k > 1, the outer edge of the ring is radius - u(this).
STEAMI_GAUGE_RING_INSET = const(4)

# --- Graph widget layout ---
STEAMI_GRAPH_MARGIN = const(15)
STEAMI_GRAPH_X_OFFSET = const(6)
STEAMI_GRAPH_Y = const(38)
STEAMI_GRAPH_HEIGHT = const(52)
STEAMI_GRAPH_VALUE_Y = const(31)
STEAMI_GRAPH_DASH = const(3)
STEAMI_GRAPH_GAP = const(3)
# When k > 1, the axis labels' gap to the top, their line and the axis.
STEAMI_GRAPH_LABEL_PAD = const(2)

# --- Menu widget ---
# The bar of the selected item starts this far above its row.
STEAMI_MENU_BAR_PAD = const(2)

# --- Watch widget: half width of the hand bases ---
STEAMI_WATCH_HOUR_HALF_W = const(3)
STEAMI_WATCH_MINUTE_HALF_W = const(2)
