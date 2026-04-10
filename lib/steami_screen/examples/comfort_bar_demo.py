"""
Shows temperature with a bar graph indicating how close it is to 40°C.
"""

from time import sleep_ms

import ssd1327
from hts221 import HTS221
from machine import I2C, SPI, Pin
from steami_screen import GREEN, Screen, SSD1327Display

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
sensor = HTS221(i2c)

# --- Main loop ---
while True:
    temp = round(sensor.temperature(), 1)

    screen.clear()
    screen.title("Temp")

    screen.value(temp, unit="C", label="TEMP")
    screen.bar(temp, max_val=40, color=GREEN)

    screen.show()

    sleep_ms(100)
