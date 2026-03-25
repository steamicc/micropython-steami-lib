"""Show the effect of the built-in heater (enable_heater()): read humidity before, enable heater for a few seconds, read again. The heater evaporates condensation — humidity should drop. Demonstrates a feature unique to this sensor."""
from time import sleep

from machine import I2C
from wsen_hids import WSEN_HIDS

i2c = I2C(1)
sensor = WSEN_HIDS(i2c)

# Read before heater
humidity_before, temperature_before = sensor.read_one_shot()

print("Before heater:")
print("Humidity: {:.2f} %RH".format(humidity_before))
print("Temperature: {:.2f} °C".format(temperature_before))
print()

# Enable heater
print("Heater ON...")
sensor.enable_heater(True)

# Wait a few seconds to see the effect
sleep(10)

# New reading
humidity_after, temperature_after = sensor.read_one_shot()

# Disable the heater
sensor.enable_heater(False)
print("Heater OFF")
print()

print("After heater:")
print("Humidity: {:.2f} %RH".format(humidity_after))
print("Temperature: {:.2f} °C".format(temperature_after))
print()

print("Delta humidity: {:.2f} %RH".format(humidity_after - humidity_before))
print("Delta temperature: {:.2f} °C".format(temperature_after - temperature_before))
