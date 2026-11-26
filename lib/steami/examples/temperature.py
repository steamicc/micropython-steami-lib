"""Print the temperature once per second.

Works on every release: the BME280 on a V1c, the WSEN-HIDS (then the WSEN-PADS)
on a V1a or V1b. chip() tells which one answered. The value is in degrees
Celsius, with the calibration of the board config applied when there is one.

If no sensor answers, begin() returns False and error() says why; the library
also prints one message with its code.
"""

import math
from time import sleep

from steami import Temperature

temperature = Temperature()

if temperature.begin():
    print("Temperature sensor:", temperature.chip())
else:
    print("No temperature sensor:", temperature.error())

while True:
    celsius = temperature.read()
    if not math.isnan(celsius):
        print("{:.1f} C".format(celsius))
    sleep(1)
