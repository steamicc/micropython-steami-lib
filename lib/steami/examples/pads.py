"""Use the crocodile pads P24, P25, P28 and P29 of the MCP23009E expander.

These four pads are GPIO 0 to 3 of the expander, not pins of the MCU: they are
driven through MCP23009Pin, which works like machine.Pin. Works on every
release (V1a, V1b and V1c).

The expander outputs are open-drain: they sink current to GND but cannot
source it, so the LED goes from 3V3 to the pad and lights when the pad is
driven to 0.

Wiring: an LED with a 220 ohm resistor from 3V3 to P28 (anode on 3V3, cathode
on P28), and a crocodile wire that touches P24 to GND. The LED lights while P24
is grounded, and the buzzer beeps once (100 ms) each time the contact is made.
"""

from time import sleep_ms

from mcp23009e import MCP23009Pin
from steami import PAD_P24, PAD_P28, Steami, no_tone, tone

mcp = Steami.mcp23009e()
if mcp is None:
    raise SystemExit("The MCP23009E expander (I2C 0x20) did not answer.")

contact = MCP23009Pin(mcp, PAD_P24, MCP23009Pin.IN, MCP23009Pin.PULL_UP)
led = MCP23009Pin(mcp, PAD_P28, MCP23009Pin.OUT, value=1)  # 1 = released, LED off

last = None
try:
    while True:
        grounded = contact.value() == 0
        if grounded != last:
            led.value(0 if grounded else 1)
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
    led.value(1)
