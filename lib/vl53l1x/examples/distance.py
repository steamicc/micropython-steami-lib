from machine import I2C
from vl53l1x import VL53L1X
import time

i2c = I2C(1)
distance = VL53L1X(i2c)
while True:
    print("range: %s mm " % distance.read())
    time.sleep_ms(50)
