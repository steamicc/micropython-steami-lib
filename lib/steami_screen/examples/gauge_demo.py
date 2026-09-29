"""Gauge demo example using VL53L1X distance sensor and SSD1327 OLED.

Displays time-of-flight distance as an arc gauge on the round screen.
The gauge color and arc width change dynamically based on the measured
distance, providing a clear visual proximity indicator.

Color zones:
    WHITE  → object very close  (< 150 mm)
    YELLOW → object at medium range (< 350 mm)
    LIGHT  → object far away   (>= 350 mm)

    Note: on SSD1327, WHITE/YELLOW/LIGHT degrade to grayscale (gray4=15/9/11).
    Visual distinction relies on brightness differences between gray levels.
    If contrast is insufficient on hardware, arc_width variation alone may
    be a clearer proximity indicator than color transitions.

Arc width:
    Thicker arc when close, thinner when far.

Reactivity:
    The display uses a partial redraw strategy:
    - The gauge arc is redrawn only when color or arc_width changes,
      by clearing the inner circle area and redrawing the arc.
    - The center text is erased and redrawn on every distance update.
    - The subtitle label is redrawn after each gauge update.
    The loop cadence (30 ms) is chosen to match the effective SSD1327
    refresh rate while remaining visually fluid.
"""

from time import sleep_ms

import ssd1327
from machine import I2C, SPI, Pin
from steami_screen import BLACK, LIGHT, WHITE, YELLOW, Screen, SSD1327Display
from vl53l1x import VL53L1X

# === Display setup ===
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")
display = SSD1327Display(ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs))
screen = Screen(display)

# === Sensor setup ===
i2c = I2C(1)
sensor = VL53L1X(i2c)

# === Constants ===
MAX_DIST = 500
REDRAW_THRESHOLD = 10  # mm — minimum change to trigger a redraw

# === Center text area (erased before each text update) ===
_TEXT_W = 56
_TEXT_H = 10
_TEXT_X = screen.center[0] - _TEXT_W // 2
_TEXT_Y = screen.center[1] - _TEXT_H // 2


def dist_to_color(dist):
    """Return gauge color based on measured distance."""
    if dist < 150:
        return WHITE
    elif dist < 350:
        return YELLOW
    else:
        return LIGHT


def dist_to_arc_width(dist):
    """Return arc width based on distance — thicker when closer."""
    ratio = 1.0 - max(0.0, min(1.0, dist / MAX_DIST))
    return int(5 + ratio * 12)


def redraw_gauge(dist, color, arc_w):
    """Erase the gauge area and redraw arc + subtitle."""
    cx, cy = screen.center
    # Erase inner area (everything inside the arc ring)
    screen.circle(cx, cy, screen.radius - 1, BLACK, fill=True)
    # Redraw gauge arc
    screen.gauge(dist, min_val=0, max_val=MAX_DIST, color=color, arc_width=arc_w)
    # Redraw static subtitle (erased by the circle fill)
    screen.subtitle("Distance")


def redraw_text(dist):
    """Erase and redraw only the center distance text."""
    screen.rect(_TEXT_X, _TEXT_Y, _TEXT_W, _TEXT_H, BLACK, fill=True)
    screen.text(f"{dist} mm", at="CENTER")


# === Startup ===
screen.clear()
screen.show()

# === Main loop ===
last_dist = -1
last_color = None
last_arc_w = None

try:
    while True:
        dist = sensor.read()

        if abs(dist - last_dist) >= REDRAW_THRESHOLD:
            color = dist_to_color(dist)
            arc_w = dist_to_arc_width(dist)

            # Redraw gauge only if visual style changed
            if color != last_color or arc_w != last_arc_w:
                redraw_gauge(dist, color, arc_w)
                last_color = color
                last_arc_w = arc_w

            # Always update center text
            redraw_text(dist)

            screen.show()
            last_dist = dist

        sleep_ms(30)

except KeyboardInterrupt:
    pass
finally:
    screen.clear()
    screen.show()
