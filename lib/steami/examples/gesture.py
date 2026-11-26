"""Print each hand gesture seen by the APDS-9960.

V1a and V1b only. A V1c has no gesture sensor: begin() returns False and the
library prints one message ending in (E20).

Move a hand above the sensor: LEFT, RIGHT, UP, DOWN, NEAR or FAR. Nothing is
printed while there is no gesture. begin() turns the gesture engine on, and
while it tracks a hand the light and colour readings freeze.
"""

from steami import Gesture

gesture = Gesture()

if gesture.begin():
    print("Gesture sensor:", gesture.chip())
else:
    print("No gesture sensor:", gesture.error())

while True:
    direction = gesture.read(200)
    if direction != Gesture.NONE:
        print(Gesture.name(direction))
