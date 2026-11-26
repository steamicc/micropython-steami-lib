"""Print the acceleration measured by the ISM330DL five times per second.

Works on every release (V1a, V1b and V1c). Values are in g, and begin() sets the
shared accelerometer to +-8 g at 104 Hz. strength() is the norm, and
is_shaken() is true above 2 g.

If the sensor does not answer, begin() returns False and error() says why; the
library also prints one message with its code.
"""

from time import sleep_ms

from steami import Accelerometer

accelerometer = Accelerometer()

if accelerometer.begin():
    print("Accelerometer:", accelerometer.chip())
else:
    print("No accelerometer:", accelerometer.error())

while True:
    x, y, z = accelerometer.read()
    print(
        "x={:.2f} y={:.2f} z={:.2f} g, strength {:.2f}{}".format(
            x, y, z, accelerometer.strength(), " SHAKEN" if accelerometer.is_shaken() else ""
        )
    )
    sleep_ms(200)
