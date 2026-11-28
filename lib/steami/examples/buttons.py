"""Print the presses and releases of the seven buttons (A, B, MENU and the D-pad).

Works on every release (V1a, V1b and V1c). A tap made between two calls is not
missed, however long the loop waits: A, B and MENU are caught by an interrupt,
the D-pad by the latch of its expander. On every button, the press and the
release of such a tap are seen by the same call.

was_pressed() and was_released() are flags: several taps between two calls
give one. get_presses() counts every press, so this example uses it for the
presses and prints how many came since the last turn and the total: a slow
loop (one that also draws on the screen, for example) still counts every tap
of A, B and MENU. On the D-pad, two taps between two calls still count as one:
the expander keeps the first change only.

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
totals = [0] * len(NAMES)

while True:
    for k, name in enumerate(NAMES):
        presses = buttons.get_presses(name)
        if presses:
            totals[k] += presses
            print(name, "pressed (+{}, total {})".format(presses, totals[k]))
        if buttons.was_released(name):
            print(name, "released")
    sleep_ms(5)
