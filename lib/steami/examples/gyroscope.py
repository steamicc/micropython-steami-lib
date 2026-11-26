"""Print the angular speed measured by the ISM330DL five times per second.

Works on every release (V1a, V1b and V1c). Values are in degrees per second;
they stay close to 0 while the board lies still.

If the sensor does not answer, begin() returns False and error() says why; the
library also prints one message with its code.
"""

from time import sleep_ms

from steami import Gyroscope

gyroscope = Gyroscope()

if gyroscope.begin():
    print("Gyroscope:", gyroscope.chip())
else:
    print("No gyroscope:", gyroscope.error())

while True:
    x, y, z = gyroscope.read()
    print("x={:.1f} y={:.1f} z={:.1f} dps".format(x, y, z))
    sleep_ms(200)
