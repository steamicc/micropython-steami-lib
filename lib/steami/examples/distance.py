"""Print the distance measured by the VL53L1X once per second.

Works on every release (V1a, V1b and V1c). read() gives millimetres, or -1 when
the sensor timed out, sees no target or is unavailable.

If the sensor does not answer, begin() returns False and error() says why; the
library also prints one message with its code.
"""

from time import sleep

from steami import Distance

distance = Distance()

if distance.begin():
    print("Distance sensor:", distance.chip())
else:
    print("No distance sensor:", distance.error())

while True:
    mm = distance.read()
    if mm >= 0:
        print("{} mm ({:.1f} cm)".format(mm, distance.cm()))
    else:
        print("no result")
    sleep(1)
