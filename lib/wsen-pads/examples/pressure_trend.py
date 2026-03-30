"""Read pressure every 10s, keep the last 10 values in a list, print whether pressure is rising, falling, or stable (useful for simple weather prediction)"""

from time import sleep

from machine import I2C
from wsen_pads import WSEN_PADS
from wsen_pads.const import ODR_10_HZ

i2c = I2C(1)
sensor = WSEN_PADS(i2c)

sensor.set_continuous(odr=ODR_10_HZ)

pressure_history = []
MAX_VALUES = 10
THRESHOLD = 0.5  # sensitivity (hPa)

def get_trend(values):
    if len(values) < 2:
        return "N/A"

    half = len(values) // 2
    first_half_avg = sum(values[:half]) / len(values[:half])
    second_half_avg = sum(values[half:]) / len(values[half:])

    diff = second_half_avg - first_half_avg

    if abs(diff) < THRESHOLD:
        return "stable"
    elif diff > 0:
        return "rising"
    else:
        return "falling"

while True:
    pressure = sensor.pressure_hpa()

    # store value
    pressure_history.append(pressure)

    # keep only last 10 values
    if len(pressure_history) > MAX_VALUES:
        pressure_history.pop(0)

    trend = get_trend(pressure_history)

    print("P:", pressure, "hPa, Pressure is", trend)

    sleep(10)
