"""Print each press and release of the seven buttons (A, B, MENU and the D-pad).

Works on every release (V1a, V1b and V1c). A press is seen as soon as one call
happens while the button is down, so the loop calls the buttons often (at least
every 50 ms: a quick tap lasts about 100 ms) and does not wait.

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
