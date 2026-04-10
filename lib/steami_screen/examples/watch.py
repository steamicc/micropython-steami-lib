"""
Tutorial 09 — Analog Watch
Displays an analog clock face using the built-in RTC.
"""

import time

import ssd1327
from machine import RTC, SPI, Pin
from steami_screen import Screen, SSD1327Display

# --- Screen setup ---
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

display = SSD1327Display(ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs))
screen = Screen(display)

# --- RTC setup ---
rtc = RTC()

# --- Main loop ---
while True:
    _, _, _, _, h, m, s, _ = rtc.datetime()

    screen.clear()
    screen.watch(h, m, s)
    screen.show()

    time.sleep(0.5)
