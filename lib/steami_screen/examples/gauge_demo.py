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
    The display is redrawn only when the distance changes by more than
    REDRAW_THRESHOLD mm, avoiding unnecessary SPI transfers.
    The loop cadence (30 ms) is chosen to match the effective SSD1327
    refresh rate while remaining visually fluid.
"""

from time import sleep_ms

import ssd1327
from machine import I2C, SPI, Pin
from steami_screen import LIGHT, WHITE, YELLOW, Screen, SSD1327Display
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


def redraw(dist):
    """Redraw the full gauge screen.

    Note: each call performs a full-screen refresh (clear + gauge + text + show).
    Partial redraw would reduce SPI transfer cost but requires lower-level
    arc delta tracking. This remains the main rendering bottleneck.
    """
    color = dist_to_color(dist)
    arc_w = dist_to_arc_width(dist)
    screen.clear()
    screen.gauge(dist, min_val=0, max_val=MAX_DIST, color=color, arc_width=arc_w)
    screen.text(f"{dist} mm", at="CENTER")
    screen.subtitle("Distance")
    screen.show()


# === Main loop ===
last_dist = -1
try:
    while True:
        dist = sensor.read()
        if abs(dist - last_dist) >= REDRAW_THRESHOLD:
            last_dist = dist
            redraw(dist)
        sleep_ms(30)  # matches effective SSD1327 refresh rate
except KeyboardInterrupt:
    pass
finally:
    screen.clear()
    screen.show()
