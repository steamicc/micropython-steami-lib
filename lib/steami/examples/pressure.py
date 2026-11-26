"""Print the pressure in hPa and the altitude in metres once per second.

Works on every release: the BME280 on a V1c, the WSEN-PADS on a V1a or V1b.
chip() tells which one answered. The altitude comes from the same formula on
every release, with the standard sea-level pressure of 1013.25 hPa; pass your
local value to altitude() for a better figure.

If no sensor answers, begin() returns False and error() says why; the library
also prints one message with its code.
"""

import math
from time import sleep

from steami import Pressure

pressure = Pressure()

if pressure.begin():
    print("Pressure sensor:", pressure.chip())
else:
    print("No pressure sensor:", pressure.error())

while True:
    hpa = pressure.read()
    if not math.isnan(hpa):
        print("{:.1f} hPa, {:.0f} m".format(hpa, pressure.altitude()))
    sleep(1)
