"""Compute and display the dew point temperature from humidity + temperature using the Magnus formula.
Useful to understand when condensation might occur."""
from math import log

from machine import I2C
from wsen_hids import WSEN_HIDS

i2c = I2C(1)
sensor = WSEN_HIDS(i2c)


def dew_point_celsius(temperature_c, humidity):
    # Magnus formula
    a = 17.62
    b = 243.12  # °C

    # Clamp humidity to a small positive value to avoid log(0) when humidity is 0.0
    safe_humidity = max(humidity, 0.01)
    gamma = (a * temperature_c / (b + temperature_c)) + log(safe_humidity / 100.0)
    dp = (b * gamma) / (a - gamma)
    return dp


humidity, temperature = sensor.read_one_shot()
dew_point = dew_point_celsius(temperature, humidity)

print("Humidity: {:.2f} %RH".format(humidity))
print("Temperature: {:.2f} °C".format(temperature))
print("Dew point: {:.2f} °C".format(dew_point))
