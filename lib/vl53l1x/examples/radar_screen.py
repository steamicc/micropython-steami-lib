"""Radar screen example using VL53L1X and SSD1327 OLED.

Displays a real-time distance bar on the screen. The closer the object,
the longer and brighter the bar, similar to a car parking sensor.
Adapted for a round display bezel using steami_screen widgets.
"""

import sys

import micropython

sys.path.insert(0, "/remote")

from time import sleep_ms

import ssd1327
from machine import I2C, SPI, Pin
from steami_screen import DARK, GRAY, LIGHT, RED, Screen, SSD1327Display
from vl53l1x import VL53L1X

# === Constants ===
MAX_DISTANCE_MM = 1000

# === Display ===
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")
display = SSD1327Display(ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs))
screen = Screen(display)

# === Sensor ===
i2c = I2C(1)
tof = VL53L1X(i2c)


@micropython.native
def compute_display(distance):
    """Compute proximity and color from distance value.

    Returns (proximity, color) or (None, None) if out of range.
    """
    if distance > MAX_DISTANCE_MM:
        return None, None
    proximity = MAX_DISTANCE_MM - distance
    if proximity > 700:
        color = RED
    elif proximity > 400:
        color = LIGHT
    else:
        color = GRAY
    return proximity, color


try:
    while True:
        distance = tof.read()

        screen.clear()
        screen.title("RADAR")

        proximity, color = compute_display(distance)

        if proximity is None:
            screen.gauge(0, min_val=0, max_val=MAX_DISTANCE_MM, color=DARK)
            screen.value("----", unit="mm")
            screen.subtitle("Out of range")
        else:
            screen.gauge(proximity, min_val=0, max_val=MAX_DISTANCE_MM, color=color)
            screen.value(str(distance), unit="mm")
            screen.subtitle("Distance")

        screen.show()
        sleep_ms(50)

except KeyboardInterrupt:
    pass

finally:
    screen.clear()
    screen.show()
