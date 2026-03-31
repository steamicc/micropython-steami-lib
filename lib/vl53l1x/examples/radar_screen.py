"""Radar screen example using VL53L1X and SSD1327 OLED.

Displays a real-time distance bar on the screen. The closer the object,
the longer and brighter the bar, similar to a car parking sensor.
Adapted for a round display bezel.
"""

from time import sleep_ms

import ssd1327
from machine import I2C, SPI, Pin
from vl53l1x import VL53L1X

MAX_DISTANCE_MM = 1000

# Layout constants for the round screen
BAR_X = 24
BAR_Y = 70
BAR_MAX_WIDTH = 80
BAR_HEIGHT = 15
TEXT_LBL_X = 28
TEXT_LBL_Y = 35
TEXT_VAL_X = 36
TEXT_VAL_Y = 50
TEXT_OUT_X = 16  # Shifted left to fit the longer "Out of range" text

i2c = I2C(1)
tof = VL53L1X(i2c)

spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)

try:
    while True:
        distance = tof.read()

        # Clear the display frame buffer
        display.fill(0)

        # Clamp distance to maximum range and compute integer proximity
        clamped_dist = max(0, min(distance, MAX_DISTANCE_MM))
        proximity = MAX_DISTANCE_MM - clamped_dist

        # Map proximity to bar width (max 80px) and brightness (max 15)
        bar_width = (80 * proximity) // MAX_DISTANCE_MM
        brightness = (15 * proximity) // MAX_DISTANCE_MM

        # If the object is within the detection range, ensure minimum visibility
        if distance <= MAX_DISTANCE_MM:
            bar_width = max(1, bar_width)
            brightness = max(1, brightness)

        # Draw the outline box (1 pixel larger than the max bar size) at max brightness
        display.framebuf.rect(BAR_X - 1, BAR_Y - 1, BAR_MAX_WIDTH + 2, BAR_HEIGHT + 2, 15)
        # Draw the distance bar centered: x=24, y=70, max_width=80, height=15
        display.framebuf.fill_rect(BAR_X, BAR_Y, bar_width, BAR_HEIGHT, brightness)

        # Display distance or "Out of range"
        if distance > MAX_DISTANCE_MM:
            display.text("Out of range", TEXT_OUT_X, TEXT_VAL_Y, 15)
        else:
            display.text("{} mm".format(distance), TEXT_VAL_X, TEXT_VAL_Y, 15)

        # Send the buffer to the physical screen
        display.show()

        sleep_ms(50)

except KeyboardInterrupt:
    pass
finally:
    # Clear the screen on exit or error
    display.fill(0)
    display.show()
