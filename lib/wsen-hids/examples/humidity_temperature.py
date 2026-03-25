"""Simple read: print humidity and temperature once (beginner-friendly first example)"""

from machine import I2C
from wsen_hids import WSEN_HIDS

# Initialise le bus I2C
i2c = I2C(1)

# Initialise le capteur
sensor = WSEN_HIDS(i2c)

# Lecture unique
humidity, temperature = sensor.read_one_shot()

print("Humidity: {:.2f} %RH".format(humidity))
print("Temperature: {:.2f} °C".format(temperature))
