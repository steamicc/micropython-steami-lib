from machine import I2C, Pin
from time import sleep
from wsen_pads import WSEN_PADS

i2c = I2C(1)

sensor = WSEN_PADS(i2c)

for _ in range(10):
    pressure, temperature = sensor.read_one_shot()

    print("P:", pressure, "hPa  T:", temperature, "°C")

    sleep(0.5)
