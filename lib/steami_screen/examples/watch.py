"""
Tutorial 09 — Analog Watch
Displays an analog clock face using the built-in RTC.
"""

import time

from machine import RTC
from steami import Screen

# --- Screen setup ---
screen = Screen()
screen.begin()  # allocate the frame buffer early in the program

# --- RTC setup ---
rtc = RTC()

# --- Main loop ---
while True:
    _, _, _, _, h, m, s, _ = rtc.datetime()

    screen.clear()
    screen.watch(h, m, s)
    screen.show()

    time.sleep(0.5)
