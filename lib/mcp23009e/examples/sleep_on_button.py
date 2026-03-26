"""
Low-power wake-on-button demo using the MCP23009E interrupt output.

The board enters light sleep and wakes up when any D-PAD button is pressed.
After wake-up, the script prints which button caused the wake event and how long
the board slept.

This example assumes the expander interrupt line is connected to a wake-capable
MCU pin named "INT_EXPANDER".
"""

from time import sleep_ms, ticks_diff, ticks_ms

from machine import I2C, Pin, lightsleep
from mcp23009e import MCP23009E
from mcp23009e.const import *

bus = I2C(1)
reset = Pin("RST_EXPANDER", Pin.OUT)
interrupt = Pin("INT_EXPANDER", Pin.IN)

mcp = MCP23009E(
    bus,
    address=MCP23009_I2C_ADDR,
    reset_pin=reset,
    interrupt_pin=interrupt,
)

BUTTONS = {
    MCP23009_BTN_UP: "UP",
    MCP23009_BTN_DOWN: "DOWN",
    MCP23009_BTN_LEFT: "LEFT",
    MCP23009_BTN_RIGHT: "RIGHT",
}

wake_button = None


def make_callback(name):
    def callback():
        global wake_button
        wake_button = name

    return callback


for pin_number, name in BUTTONS.items():
    mcp.setup(pin_number, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)
    mcp.interrupt_on_falling(pin_number, make_callback(name))

print("=================================")
print("Sleep on Button")
print("=================================\n")
print("Press any D-PAD button to wake the board.\n")

while True:
    wake_button = None
    start = ticks_ms()

    # Wait until all buttons are released before sleeping
    while True:
        if all(mcp.get_level(pin_number) == MCP23009_LOGIC_HIGH for pin_number in BUTTONS):
            break
        sleep_ms(20)

    print("Going to light sleep...")

    # Duration can be removed if your platform supports external wake-up only.
    lightsleep(60000)

    slept_ms = ticks_diff(ticks_ms(), start)

    # Give the expander interrupt logic a short time to settle
    sleep_ms(20)

    if wake_button is None:
        intf = mcp.get_intf()      # which pins triggered
        intcap = mcp.get_intcap()  # latched GPIO state at interrupt time

        for pin_number, name in BUTTONS.items():
            mask = 1 << pin_number
            if (intf & mask) and not (intcap & mask):
                wake_button = name
                break

    print("Woke up after", slept_ms, "ms")
    print("Wake source:", wake_button if wake_button else "unknown")
    print()
