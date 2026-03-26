"""
Spatial field mapping.
Print X, Y, Z field values and magnitude as a formatted table, updating every 500ms.
Move the board around to see how the field changes.
Includes min/max tracking for each axis to show the range explored.
"""

from math import sqrt
from time import sleep_ms

from lis2mdl import LIS2MDL
from machine import I2C


def update_minmax(value, current_min, current_max):
    current_min = min(current_min, value)
    current_max = max(current_max, value)
    return current_min, current_max


i2c = I2C(1)
mag = LIS2MDL(i2c)

x_min = y_min = z_min = 1e9
x_max = y_max = z_max = -1e9

print("Field map example")
print("Move the board around and watch how the field changes.")
print()

header = "{:>8} {:>8} {:>8} {:>10}   {:>17} {:>17} {:>17}".format(
    "X(uT)", "Y(uT)", "Z(uT)", "|B|(uT)",
    "X range", "Y range", "Z range"
)
print(header)
print("-" * len(header))

while True:
    x_ut, y_ut, z_ut = mag.magnetic_field_ut()
    magnitude = sqrt(x_ut * x_ut + y_ut * y_ut + z_ut * z_ut)

    x_min, x_max = update_minmax(x_ut, x_min, x_max)
    y_min, y_max = update_minmax(y_ut, y_min, y_max)
    z_min, z_max = update_minmax(z_ut, z_min, z_max)

    print(
        "{:8.2f} {:8.2f} {:8.2f} {:10.2f}   {:>17} {:>17} {:>17}".format(
            x_ut,
            y_ut,
            z_ut,
            magnitude,
            "[{:.2f}, {:.2f}]".format(x_min, x_max),
            "[{:.2f}, {:.2f}]".format(y_min, y_max),
            "[{:.2f}, {:.2f}]".format(z_min, z_max),
        )
    )

    sleep_ms(500)
