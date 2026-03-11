from machine import I2C, Pin
from time import sleep

from wsen_hids import WSEN_HIDS

i2c = I2C(1)

sensor = WSEN_HIDS(i2c)

sensor.set_continuous_mode(WSEN_HIDS.ODR_1_HZ)

for _ in range(10):
    humidity, temperature = sensor.read()

    print("Humidity: {:.2f} %RH".format(humidity))
    print("Temperature: {:.2f} °C".format(temperature))
    print()

    sleep(1)
