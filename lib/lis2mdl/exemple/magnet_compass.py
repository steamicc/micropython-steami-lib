# exemple of heading reading with direction label
from time import sleep_ms
from machine import I2C
from lis2mdl.device import LIS2MDL
from lis2mdl.const import *

i2c = I2C(1)
mag = LIS2MDL(i2c)

while True:
    angle = mag.heading_flat_only()
    direction = mag.direction_label(angle)
    print("Cap:", angle, "°", "-", direction)
    sleep_ms(100)
