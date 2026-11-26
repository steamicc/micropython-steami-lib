"""Print the light level measured by the APDS-9960 twice per second.

V1a and V1b only. A V1c has no light sensor: begin() returns False and the
library prints one message ending in (E20).

read() is the raw clear count of the sensor, higher in brighter light (not a lux
value). The reading freezes while a hand is tracked by Gesture.
"""

from time import sleep_ms

from steami import Light

light = Light()

if light.begin():
    print("Light sensor:", light.chip())
else:
    print("No light sensor:", light.error())

while True:
    print("light", light.read())
    sleep_ms(500)
