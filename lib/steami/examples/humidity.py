"""Print the relative humidity once per second.

Works on every release: the BME280 on a V1c, the WSEN-HIDS on a V1a or V1b.
chip() tells which one answered.

If no sensor answers, begin() returns False and error() says why; the library
also prints one message with its code.
"""

import math
from time import sleep

from steami import Humidity

humidity = Humidity()

if humidity.begin():
    print("Humidity sensor:", humidity.chip())
else:
    print("No humidity sensor:", humidity.error())

while True:
    percent = humidity.read()
    if not math.isnan(percent):
        print("{:.1f} %RH".format(percent))
    sleep(1)
