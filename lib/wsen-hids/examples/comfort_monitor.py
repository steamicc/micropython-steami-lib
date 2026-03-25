"""Loop that reads humidity + temperature every 2s and prints a comfort indicator ("Dry", "Comfortable", "Humid")
based on humidity thresholds (< 30%, 30-60%, > 60%)"""

from time import sleep_ms

from machine import I2C
from wsen_hids import WSEN_HIDS

i2c = I2C(1)
sensor = WSEN_HIDS(i2c)


def comfort_label(humidity):
    if humidity < 30:
        return "Dry"
    elif humidity <= 60:
        return "Comfortable"
    else:
        return "Humid"

while True:
    humidity, temperature = sensor.read_one_shot()
    comfort = comfort_label(humidity)

    print("Humidity: {:.2f} %RH".format(humidity))
    print("Temperature: {:.2f} °C".format(temperature))
    print("Comfort: {}".format(comfort))
    print()

    sleep_ms(2000)
