"""
Displays a compass with a rotating needle based on the LIS2MDL magnetometer.
"""

from time import sleep_ms

from lis2mdl import LIS2MDL
from machine import I2C
from steami import Screen

# --- Screen setup ---
screen = Screen()
screen.begin()  # allocate the frame buffer early in the program

# --- Sensor setup ---
i2c = I2C(1)
sensor = LIS2MDL(i2c)

print("Calibrate the magnetometer by moving it flat.")
sensor.calibrate_minmax_2d()
print("Calibration complete.")

# Smooth the heading: the raw value jitters by a few degrees on a still board.
sensor.set_heading_filter(0.2)

heading = 0

# --- Main loop ---
while True:
    angle = sensor.heading_flat_only()

    screen.clear()
    screen.compass(angle)
    screen.show()

    print("Cap:", angle, "°")

    sleep_ms(50)
