"""Radar screen example using VL53L1X and the board screen.

Displays a real-time distance bar on the screen. The closer the object,
the longer and brighter the bar, similar to a car parking sensor.
Adapted for a round display bezel using steami_screen widgets.

The screen is steami.Screen: the SSD1327 OLED on V1a/V1b, the round GC9A01
TFT on V1c.
"""

from time import sleep_ms

from machine import I2C
from steami import Screen
from steami_screen import DARK, GRAY, LIGHT, RED
from vl53l1x import VL53L1X

# === Constants ===
MAX_DISTANCE_MM = 1000

# === Display ===
screen = Screen()
screen.begin()  # allocate the frame buffer early in the program

# === Sensor ===
i2c = I2C(1)
tof = VL53L1X(i2c)


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

        proximity, color = compute_display(distance)

        # Draw gauge first so that title/value text layers on top of the arc
        if proximity is None:
            screen.gauge(0, min_val=0, max_val=MAX_DISTANCE_MM, color=DARK)
        else:
            screen.gauge(proximity, min_val=0, max_val=MAX_DISTANCE_MM, color=color)

        screen.title("RADAR")

        if proximity is None:
            screen.value("----", unit="mm")
            screen.subtitle("Out of range")
        else:
            screen.value(str(distance), unit="mm")
            screen.subtitle("Proximity")

        screen.show()
        sleep_ms(50)

except KeyboardInterrupt:
    pass

finally:
    screen.clear()
    screen.show()
