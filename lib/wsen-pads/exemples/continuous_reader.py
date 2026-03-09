from machine import I2C, Pin
from time import sleep
from wsen_pads import WSEN_PADS
from wsen_pads.const import ODR_10_HZ

i2c = I2C(1)

sensor = WSEN_PADS(i2c)

sensor.set_continuous(odr=ODR_10_HZ)

for _ in range(10):
    pressure = sensor.pressure()
    temperature = sensor.temperature()

    print("P:", pressure, "hPa  T:", temperature, "°C")

    sleep(0.5)