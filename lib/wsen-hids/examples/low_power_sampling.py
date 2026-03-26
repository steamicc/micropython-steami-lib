"""Low-power sampling with power_off() between readings.

Minimises energy consumption by powering the sensor down between
one-shot measurements taken every 10 seconds.  Displays humidity,
temperature, free RAM and measurement duration to illustrate a
battery-friendly sampling pattern.

Requires firmware >= v0.1.0 (fix for power_off/power_on cycle, #238).
"""

import gc
from time import sleep, ticks_diff, ticks_ms

from machine import I2C
from wsen_hids import WSEN_HIDS

i2c = I2C(1)
sensor = WSEN_HIDS(i2c)

while True:
    gc.collect()
    t0 = ticks_ms()

    # Wake the sensor, take a single measurement, then power down
    sensor.power_on()
    humidity, temperature = sensor.read_one_shot()
    sensor.power_off()

    elapsed_ms = ticks_diff(ticks_ms(), t0)

    print("Humidity:    {:.2f} %RH".format(humidity))
    print("Temperature: {:.2f} C".format(temperature))
    print("Free RAM:    {} bytes".format(gc.mem_free()))
    print("Measurement: {} ms".format(elapsed_ms))
    print()

    sleep(10)
