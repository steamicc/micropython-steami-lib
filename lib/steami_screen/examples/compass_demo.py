"""
Displays a compass with a rotating needle based on the LIS2MDL magnetometer.
"""

from time import sleep_ms

import ssd1327
from lis2mdl import LIS2MDL
from machine import I2C, SPI, Pin
from steami_screen import Screen, SSD1327Display

# --- Screen setup ---
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

raw_display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)
display = SSD1327Display(raw_display)
screen = Screen(display)

# --- Sensor setup ---
i2c = I2C(1)
sensor = LIS2MDL(i2c)

print("Calibrate the magnetometer by moving it flat.")
sensor.calibrate_minmax_2d()
print("Calibration complete.")

heading = 0

# --- Main loop ---
while True:
    angle = sensor.heading_flat_only()

    screen.clear()
    screen.compass(angle)
    screen.show()

    print("Cap:", angle, "°")

    sleep_ms(50)
