"""
Simon Says memory game using the MCP23009E D-PAD.

Watch the sequence printed on the console, then replay it on the D-PAD.
The sequence grows by one direction every round.
"""

from time import sleep_ms

import urandom
from machine import I2C, Pin
from mcp23009e import MCP23009E
from mcp23009e.const import (
    MCP23009_BTN_DOWN,
    MCP23009_BTN_LEFT,
    MCP23009_BTN_RIGHT,
    MCP23009_BTN_UP,
    MCP23009_DIR_INPUT,
    MCP23009_I2C_ADDR,
    MCP23009_LOGIC_LOW,
    MCP23009_PULLUP,
)

bus = I2C(1)
reset = Pin("RST_EXPANDER", Pin.OUT)

mcp = MCP23009E(bus, address=MCP23009_I2C_ADDR, reset_pin=reset)

BUTTONS = {
    MCP23009_BTN_UP: "UP",
    MCP23009_BTN_DOWN: "DOWN",
    MCP23009_BTN_LEFT: "LEFT",
    MCP23009_BTN_RIGHT: "RIGHT",
}

PINS = list(BUTTONS.keys())
sequence = []


def wait_all_released():
    while True:
        released = True
        for pin_number in PINS:
            if mcp.get_level(pin_number) == MCP23009_LOGIC_LOW:
                released = False
                break
        if released:
            return
        sleep_ms(20)


def wait_for_button():
    wait_all_released()
    while True:
        for pin_number, name in BUTTONS.items():
            if mcp.get_level(pin_number) == MCP23009_LOGIC_LOW:
                while mcp.get_level(pin_number) == MCP23009_LOGIC_LOW:
                    sleep_ms(20)
                return name
        sleep_ms(20)


for pin_number in PINS:
    mcp.setup(pin_number, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)

print("=================================")
print("Simon Says")
print("=================================\n")
print("Repeat the sequence using the D-PAD.\n")

score = 0

while True:
    next_name = BUTTONS[PINS[urandom.getrandbits(8) % len(PINS)]]
    sequence.append(next_name)

    print("Sequence:")
    for item in sequence:
        print(" ", item)
        sleep_ms(500)

    print("\nYour turn:")
    success = True

    for expected in sequence:
        received = wait_for_button()
        print("You pressed:", received)
        if received != expected:
            success = False
            break

    if not success:
        print("\nWrong sequence!")
        print("Final score:", score)
        break

    score += 1
    print("Correct! Score:", score)
    print("-" * 30)
    sleep_ms(800)
