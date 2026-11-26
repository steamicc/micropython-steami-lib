"""
Shows temperature with a bar graph indicating how close it is to 40°C.
"""

from time import sleep_ms

from hts221 import HTS221
from machine import I2C
from steami import Screen
from steami_screen import GREEN

# --- Screen setup ---
screen = Screen()
screen.begin()  # allocate the frame buffer early in the program

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
