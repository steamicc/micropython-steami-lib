"""Use power_off() between readings to minimize energy consumption. Read one-shot every 10s, print values, then power down. Show gc.mem_free() and elapsed time to illustrate battery-friendly usage."""

import gc
from time import sleep, ticks_diff, ticks_ms

from machine import I2C
from wsen_hids import WSEN_HIDS

i2c = I2C(1)
sensor = WSEN_HIDS(i2c)

while True:
    gc.collect()

    t0 = ticks_ms()

    sensor.power_on()

    humidity, temperature = sensor.read_one_shot()

    sensor.power_off()

    elapsed_ms = ticks_diff(ticks_ms(), t0)

    print("Humidity: {:.2f} %RH".format(humidity))
    print("Temperature: {:.2f} °C".format(temperature))
    print("Free RAM: {} bytes".format(gc.mem_free()))
    print("Elapsed: {} ms".format(elapsed_ms))
    print()

    sleep(10)
