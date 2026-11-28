"""Print the heading measured by the LIS2MDL twice per second.

Works on every release (V1a, V1b and V1c). Hold the board flat, screen up.
heading() is in degrees clockwise from north, 0 when the top of the screen (the
USB connector side) points north, 90 for east. direction() gives
the nearest of eight sectors ("N", "NE", "E", ...).

Press MENU to calibrate for 12 seconds: turn the board slowly in every direction
meanwhile. The calibration lives in RAM and is lost on reset.

If the sensor does not answer, begin() returns False and error() says why; the
library also prints one message with its code.
"""

import math
from time import sleep_ms, ticks_diff, ticks_ms

from steami import Buttons, Compass

compass = Compass()
buttons = Buttons()

if compass.begin():
    print("Compass ready. Press MENU to calibrate (12 s).")
else:
    print("No compass:", compass.error())
buttons.begin()

last_print = ticks_ms()
while True:
    # Poll the buttons often: a short tap is missed if they are read only twice per second.
    if buttons.was_pressed("MENU"):
        print("Calibrating: turn the board in every direction...")
        compass.calibrate(12)
        print("Calibration done.")
        last_print = ticks_ms()

    if ticks_diff(ticks_ms(), last_print) >= 500:
        last_print = ticks_ms()
        heading = compass.heading()
        if math.isnan(heading):
            print("no heading")
        else:
            # Round, then wrap: 359.6 prints 0, never 360.
            print(round(heading) % 360, "deg", compass.direction())
    sleep_ms(5)
