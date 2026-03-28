"""
Simple D-PAD counter.

UP    -> increment
DOWN  -> decrement
LEFT  -> reset
RIGHT -> print current value
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

value = 0

print("=================================")
print("D-PAD Counter")
print("=================================\n")
print("UP=+1  DOWN=-1  LEFT=reset  RIGHT=print\n")

while True:
    button = wait_for_button()

    if button == "UP":
        value += 1
        print("Increment ->", value)
    elif button == "DOWN":
        value -= 1
        print("Decrement ->", value)
    elif button == "LEFT":
        value = 0
        print("Reset ->", value)
    elif button == "RIGHT":
        print("Current value ->", value)
