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

        # Clamp distance to maximum range to avoid negative ratios
        clamped_dist = max(0, min(distance, MAX_DISTANCE_MM))

        # Calculate ratio (1.0 = extremely close, 0.0 = MAX_DISTANCE_MM or further)
        ratio = 1.0 - (clamped_dist / MAX_DISTANCE_MM)

        # Map ratio to a maximum width of 80 pixels (to fit the round screen) and brightness (15 levels)
        bar_width = int(80 * ratio)
        brightness = int(15 * ratio)

        # If the object is within the detection range, ensure minimum visibility
        if distance < MAX_DISTANCE_MM:
            bar_width = max(1, bar_width)
            brightness = max(1, brightness)

        # Draw the outline box (1 pixel larger than the max bar size) at max brightness
        display.framebuf.rect(23, 69, 82, 17, 15)
        # Draw the distance bar centered: x=24, y=70, max_width=80, height=15
        display.framebuf.fill_rect(24, 70, bar_width, 15, brightness)

        # Display the text information centered in the round screen
        display.text("Distance:", 28, 35, 15)
        display.text("{} mm".format(distance), 36, 50, 15)

        # Send the buffer to the physical screen
        display.show()

        sleep_ms(50)

except KeyboardInterrupt:
    pass
finally:
    # Clear the screen on exit or error
    display.fill(0)
    display.show()
