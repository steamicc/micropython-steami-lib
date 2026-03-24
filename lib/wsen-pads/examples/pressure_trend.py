from time import sleep
from machine import I2C
from wsen_pads import WSEN_PADS
from wsen_pads.const import ODR_10_HZ

i2c = I2C(1)
sensor = WSEN_PADS(i2c)

sensor.set_continuous(odr=ODR_10_HZ)

pressure_history = []
MAX_VALUES = 10
THRESHOLD = 0.12  # sensitivity (hPa) ~ 1 meter altitude change

def get_trend(values):
    if len(values) < 2:
        return "N/A"

    diff = values[-1] - values[0]

    if abs(diff) < THRESHOLD:
        return "stable"
    elif diff > 0:
        return "falling" # pressure rising means lower altitude
    else:
        return "rising"

while True:
    pressure = sensor.pressure_hpa()

    # store value
    pressure_history.append(pressure)

    # keep only last 10 values
    if len(pressure_history) > MAX_VALUES:
        pressure_history.pop(0)

    trend = get_trend(pressure_history)

    print("P:", pressure, "hPa Trend:", trend)

    sleep(10)
