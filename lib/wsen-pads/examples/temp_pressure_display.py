"""
Read temperature and pressure, format a nice display with units and a simple bar graph using # characters to visualize pressure (e.g. 1013.2 hPa [##########-----])
"""
from time import sleep

from machine import I2C
from wsen_pads import WSEN_PADS

TEMP_MIN = 15.0
TEMP_MAX = 30.0
PRESS_MIN = 1020.0
PRESS_MAX = 1023.0


i2c = I2C(1)
sensor = WSEN_PADS(i2c)

def bar_graph(value, vmin, vmax, width=20):
    # Clamp value
    if value < vmin:
        value = vmin
    elif value > vmax:
        value = vmax

    ratio = (value - vmin) / (vmax - vmin)
    filled = int(ratio * width)

    return "[" + "#" * filled + "-" * (width - filled) + "]"

while True:
    pressure, temp = sensor.read() 
    temp_bar = bar_graph(temp, TEMP_MIN, TEMP_MAX)
    press_bar = bar_graph(pressure, PRESS_MIN, PRESS_MAX)

    line = "T:{:5.1f}°C {} | P:{:6.1f}hPa {}".format(
        temp, temp_bar, pressure, press_bar
    )

    print("\r" + line, end="")

    sleep(1)
