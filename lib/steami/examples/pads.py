"""Use the crocodile pads P24, P25, P28 and P29 of the MCP23009E expander.

These four pads are GPIO 0 to 3 of the expander, not pins of the MCU: they are
driven through MCP23009Pin, which works like machine.Pin. Works on every
release (V1a, V1b and V1c).

Wiring: an LED with a 220 ohm resistor from P28 to GND, and a crocodile wire
that touches P24 to GND. The LED lights and the buzzer beeps while P24 is
grounded.
"""

from time import sleep_ms

from mcp23009e import MCP23009Pin
from steami import PAD_P24, PAD_P28, Steami, no_tone, tone

mcp = Steami.mcp23009e()
if mcp is None:
    raise SystemExit("The MCP23009E expander (I2C 0x20) did not answer.")

contact = MCP23009Pin(mcp, PAD_P24, MCP23009Pin.IN, MCP23009Pin.PULL_UP)
led = MCP23009Pin(mcp, PAD_P28, MCP23009Pin.OUT, value=0)

last = None
try:
    while True:
        grounded = contact.value() == 0
        if grounded != last:
            led.value(grounded)
            if grounded:
                tone(880, 100)
                print("P24 grounded: LED on")
            else:
                print("P24 open: LED off")
            last = grounded
        sleep_ms(20)
except KeyboardInterrupt:
    pass
finally:
    no_tone()
    led.value(0)
