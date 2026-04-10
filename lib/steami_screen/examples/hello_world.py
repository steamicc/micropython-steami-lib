"""
hello_world.py
Basic steami_screen example:
- clear screen
- title
- value
- subtitle
- show
"""

from time import sleep_ms

import ssd1327
from machine import SPI, Pin
from steami_screen import Screen, SSD1327Display

# --- Display setup ---
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

raw_display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)
display = SSD1327Display(raw_display)
screen = Screen(display)

# --- Demo loop ---
counter = 0

while True:
    screen.clear()
    screen.title("HELLO")
    screen.subtitle("screen", "Hello world")
    screen.value(counter, label="Demo")
    screen.show()

    counter += 1
    sleep_ms(1000)
