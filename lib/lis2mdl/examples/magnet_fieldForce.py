# exemple of heading reading with direction label
from time import sleep_ms
from machine import I2C
from lis2mdl.device import LIS2MDL
from lis2mdl.const import *

i2c = I2C(1)
mag = LIS2MDL(i2c)

print("Calibrate the magnetometer by moving it in a figure-eight pattern.")
mag.calibrate_minmax_3d()
print("Calibration complete.")

while True:
    field_strength = mag.magnitude_uT()
    print("Champ magnétique :", field_strength, "µT")
    sleep_ms(100)
