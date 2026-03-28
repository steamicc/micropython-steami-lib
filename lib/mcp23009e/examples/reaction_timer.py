"""
Reaction timer game using the MCP23009E D-PAD.

Wait for "GO!", then press any D-PAD button as fast as possible.
The script measures the reaction time in milliseconds.
Best score over 5 rounds.
"""

from time import sleep_ms, ticks_diff, ticks_ms

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

pressed_button = None
press_time = None
waiting_for_press = False


def make_callback(pin_number, name):
    def callback():
        global pressed_button, press_time, waiting_for_press
        if waiting_for_press and pressed_button is None:
            pressed_button = name
            press_time = ticks_ms()

    return callback


for pin_number, name in BUTTONS.items():
    mcp.setup(pin_number, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)
    mcp.interrupt_on_falling(pin_number, make_callback(pin_number, name))

print("=================================")
print("Reaction Timer")
print("=================================\n")
print("Press any D-PAD button when GO! appears.")
print("Do not press too early.\n")

scores = []

for round_index in range(5):
    print("Round", round_index + 1)

    # Wait until all buttons are released
    while True:
        all_released = True
        for pin_number in BUTTONS:
            if mcp.get_level(pin_number) == MCP23009_LOGIC_LOW:
                all_released = False
                break
        if all_released:
            break
        sleep_ms(20)

    delay_ms = 1000 + (urandom.getrandbits(12) % 4001)
    elapsed = 0
    false_start = False

    while elapsed < delay_ms:
        for pin_number, name in BUTTONS.items():
            if mcp.get_level(pin_number) == MCP23009_LOGIC_LOW:
                print("Too early! False start on", name)
                false_start = True
                break
        if false_start:
            break
        sleep_ms(10)
        elapsed += 10

    if false_start:
        print()
        continue

    pressed_button = None
    press_time = None
    waiting_for_press = True
    go_time = ticks_ms()

    print("GO!")

    while pressed_button is None:
        sleep_ms(1)

    waiting_for_press = False
    reaction_ms = ticks_diff(press_time, go_time)
    scores.append(reaction_ms)

    print("Button:", pressed_button)
    print("Reaction time:", reaction_ms, "ms\n")

if scores:
    best = min(scores)
    average = sum(scores) // len(scores)
    print("Finished!")
    print("Valid rounds:", len(scores), "/ 5")
    print("Best:", best, "ms")
    print("Average:", average, "ms")
else:
    print("No valid round recorded.")
