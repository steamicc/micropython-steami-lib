"""
Digital combination lock using the MCP23009E D-PAD.

Enter the secret button sequence to unlock.
A wrong input resets the attempt.
"""

from time import sleep_ms

from machine import I2C, Pin
from mcp23009e import MCP23009E
from mcp23009e.const import (
    MCP23009_BTN_DOWN,
    MCP23009_BTN_LEFT,
    MCP23009_BTN_RIGHT,
    MCP23009_BTN_UP,
    MCP23009_DIR_INPUT,
    MCP23009_I2C_ADDR,
    MCP23009_LOGIC_HIGH,
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

SECRET = ["UP", "UP", "DOWN", "LEFT", "RIGHT"]


def wait_all_released():
    while True:
        if all(mcp.get_level(pin_number) == MCP23009_LOGIC_HIGH for pin_number in BUTTONS):
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


for pin_number in BUTTONS:
    mcp.setup(pin_number, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)

print("=================================")
print("Combination Lock")
print("=================================\n")
print("Enter the secret D-PAD sequence.\n")

entered = []

while True:
    button = wait_for_button()
    entered.append(button)

    print("Input:", "-".join(entered))

    expected_prefix = SECRET[: len(entered)]
    if entered != expected_prefix:
        print("WRONG")
        entered = []
        print()
        continue

    if len(entered) == len(SECRET):
        print("UNLOCKED")
        entered = []
        print()
