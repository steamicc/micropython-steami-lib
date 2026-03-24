# Example of heading reading with direction label
from time import sleep_ms

from lis2mdl.const import *
from lis2mdl.device import LIS2MDL
from machine import I2C

i2c = I2C(1)
mag = LIS2MDL(i2c)

print("Calibrate the magnetometer by moving it in a figure-eight pattern.")
mag.calibrate_minmax_3d()
print("Calibration complete.")

while True:
    angle = mag.heading_flat_only()

    direction = mag.direction_label(angle)
    print("Cap:", angle, "°", "-", direction)
    sleep_ms(100)
