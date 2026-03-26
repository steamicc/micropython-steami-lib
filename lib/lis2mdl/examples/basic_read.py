"""
Read raw magnetic field (X, Y, Z) in microtesla and temperature in a loop.
Simplest possible example — good entry point for beginners.
"""

from time import sleep_ms

from lis2mdl import LIS2MDL
from machine import I2C

i2c = I2C(1)
mag = LIS2MDL(i2c)

print("LIS2MDL basic read example")
print("Press Ctrl+C to stop.")
print()

while True:
    x_ut, y_ut, z_ut = mag.magnetic_field_ut()
    temp_c = mag.temperature()

    print(
        "Magnetic field: X={:.2f} uT  Y={:.2f} uT  Z={:.2f} uT  Temp={:.2f} C".format(
            x_ut, y_ut, z_ut, temp_c
        )
    )

    sleep_ms(500)
