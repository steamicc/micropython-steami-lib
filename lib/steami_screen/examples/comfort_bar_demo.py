"""
Shows temperature with a bar graph indicating how close it is to 40°C.

Runs on every release: steami.Temperature reads the BME280 on a V1c and the
WSEN-HIDS (then the WSEN-PADS) on a V1a or V1b.
"""

import math
from time import sleep_ms

from steami import Screen, Temperature
from steami_screen import GREEN

# --- Screen setup ---
screen = Screen()
screen.begin()  # allocate the frame buffer early in the program

# --- Sensor setup ---
temperature = Temperature()
temperature.begin()

# --- Main loop ---
while True:
    celsius = temperature.read()

    screen.clear()
    screen.title("Temp")

    if math.isnan(celsius):  # no sensor answered
        screen.value("--", unit="C", label="TEMP")
    else:
        temp = round(celsius, 1)
        screen.value(temp, unit="C", label="TEMP")
        screen.bar(temp, max_val=40, color=GREEN)

    screen.show()

    sleep_ms(100)
