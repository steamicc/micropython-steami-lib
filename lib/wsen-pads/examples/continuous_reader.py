from time import sleep

from machine import I2C
from wsen_pads import WSEN_PADS
from wsen_pads.const import ODR_10_HZ

i2c = I2C(1)

sensor = WSEN_PADS(i2c)

sensor.set_continuous(odr=ODR_10_HZ)

for _ in range(10):
    pressure = sensor.pressure_hpa()
    temperature = sensor.temperature()

    print("P:", pressure, "hPa  T:", temperature, "°C")

    sleep(0.5)
