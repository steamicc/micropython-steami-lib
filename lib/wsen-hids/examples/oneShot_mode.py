from machine import I2C, Pin
from time import sleep

from wsen_hids import WSEN_HIDS

i2c = I2C(1)

sensor = WSEN_HIDS(i2c)

for _ in range(10):
    humidity, temperature = sensor.read_one_shot()

    print("Humidity: {:.2f} %RH".format(humidity))
    print("Temperature: {:.2f} °C".format(temperature))
    print()

    sleep(1)
