"""
Binary counter using D-PAD inputs and MCP23009E GPIO outputs.

UP    -> increment
DOWN  -> decrement
LEFT  -> reset
RIGHT -> print current value

The value is displayed on GP0..GP3 as a 4-bit binary number.
"""

from time import sleep_ms

from machine import I2C, Pin
from mcp23009e import MCP23009E
from mcp23009e.const import *

bus = I2C(1)
reset = Pin("RST_EXPANDER", Pin.OUT)

mcp = MCP23009E(bus, address=MCP23009_I2C_ADDR, reset_pin=reset)

BUTTONS = {
    MCP23009_BTN_UP: "UP",
    MCP23009_BTN_DOWN: "DOWN",
    MCP23009_BTN_LEFT: "LEFT",
    MCP23009_BTN_RIGHT: "RIGHT",
}

OUTPUT_PINS = [MCP23009_GPIO1, MCP23009_GPIO2, MCP23009_GPIO3, MCP23009_GPIO4]


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


def update_outputs(value):
    for bit_index, pin_number in enumerate(OUTPUT_PINS):
        bit_value = (value >> bit_index) & 0x01
        mcp.set_level(pin_number, bit_value)


for pin_number in BUTTONS:
    mcp.setup(pin_number, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)

for pin_number in OUTPUT_PINS:
    mcp.setup(pin_number, MCP23009_DIR_OUTPUT)
    mcp.set_level(pin_number, MCP23009_LOGIC_LOW)

counter = 0
update_outputs(counter)

print("=================================")
print("Binary Counter")
print("=================================\n")
print("Displaying the 4-bit value on GP0..GP3")
print("UP=+1  DOWN=-1  LEFT=reset  RIGHT=print\n")

while True:
    button = wait_for_button()

    if button == "UP":
        counter = (counter + 1) & 0x0F
    elif button == "DOWN":
        counter = (counter - 1) & 0x0F
    elif button == "LEFT":
        counter = 0
    elif button == "RIGHT":
        pass

    update_outputs(counter)
    print("Value:", counter, " Binary:", "{:04b}".format(counter))
