"""
Displays VL53L1X time-of-flight distance with an arc gauge.
"""

from time import sleep_ms

import ssd1327
from machine import I2C, SPI, Pin
from steami_screen import BLACK, Screen, SSD1327Display
from vl53l1x import VL53L1X

# --- Display setup ---
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

raw_display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)
display = SSD1327Display(raw_display)
screen = Screen(display)

# --- Sensor setup ---
i2c = I2C(1)
sensor = VL53L1X(i2c)

# --- Main loop ---
while True:
    dist = sensor.read()

    screen.clear()
    screen.gauge(dist, min_val=0, max_val=500, color=BLACK)
    screen.value(dist, label="Distance", unit="mm")
    screen.show()

    sleep_ms(10)
