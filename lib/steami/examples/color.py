"""Print the colour measured by the APDS-9960 twice per second.

V1a and V1b only. A V1c has no colour sensor: begin() returns False and the
library prints one message ending in (E20).

read() gives the raw red, green and blue counts of the sensor as a tuple, and
(0, 0, 0) when it is unavailable. The reading freezes while a hand is tracked by
Gesture.
"""

from time import sleep_ms

from steami import Color

color = Color()

if color.begin():
    print("Colour sensor:", color.chip())
else:
    print("No colour sensor:", color.error())

while True:
    if color.is_available():
        r, g, b = color.read()
        print("r={} g={} b={}".format(r, g, b))
    else:
        print("no result")
    sleep_ms(500)
