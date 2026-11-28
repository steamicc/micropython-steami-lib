"""Print each press and release of the seven buttons (A, B, MENU and the D-pad).

Works on every release (V1a, V1b and V1c). A tap made between two calls is not
missed, however long the loop waits: A, B and MENU are caught by an interrupt,
the D-pad by the latch of its expander. At most one press per button is reported
between two calls; a D-pad tap released before the next call reads as pressed at
that call and as released at a later one.

If the D-pad expander does not answer, begin() returns False and error() says
why, but A, B and MENU still work and the arrows read as released. A button held
at start is not reported as a press.
"""

from time import sleep_ms

from steami import Buttons

buttons = Buttons()

if buttons.begin():
    print("Buttons ready.")
else:
    print("D-pad unavailable:", buttons.error())

NAMES = ("A", "B", "MENU", "UP", "DOWN", "LEFT", "RIGHT")

while True:
    for name in NAMES:
        if buttons.was_pressed(name):
            print(name, "pressed")
        if buttons.was_released(name):
            print(name, "released")
    sleep_ms(5)
