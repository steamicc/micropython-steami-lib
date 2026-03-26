"""
Morse code input using the MCP23009E D-PAD.

RIGHT short press -> dot
RIGHT long press  -> dash
LEFT              -> validate current letter
UP                -> add space / start new word
DOWN              -> clear current symbol buffer
"""

from time import sleep_ms, ticks_diff, ticks_ms

from machine import I2C, Pin
from mcp23009e import MCP23009E
from mcp23009e.const import *

bus = I2C(1)
reset = Pin("RST_EXPANDER", Pin.OUT)

mcp = MCP23009E(bus, address=MCP23009_I2C_ADDR, reset_pin=reset)

DOT_DASH_PIN = MCP23009_BTN_RIGHT
VALIDATE_PIN = MCP23009_BTN_LEFT
SPACE_PIN = MCP23009_BTN_UP
CLEAR_PIN = MCP23009_BTN_DOWN

LONG_PRESS_MS = 400

MORSE_TABLE = {
    ".-": "A",
    "-...": "B",
    "-.-.": "C",
    "-..": "D",
    ".": "E",
    "..-.": "F",
    "--.": "G",
    "....": "H",
    "..": "I",
    ".---": "J",
    "-.-": "K",
    ".-..": "L",
    "--": "M",
    "-.": "N",
    "---": "O",
    ".--.": "P",
    "--.-": "Q",
    ".-.": "R",
    "...": "S",
    "-": "T",
    "..-": "U",
    "...-": "V",
    ".--": "W",
    "-..-": "X",
    "-.--": "Y",
    "--..": "Z",
}

for pin_number in (DOT_DASH_PIN, VALIDATE_PIN, SPACE_PIN, CLEAR_PIN):
    mcp.setup(pin_number, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)

current_symbol = ""
decoded_text = ""


def wait_press_and_release(pin_number):
    while mcp.get_level(pin_number) == MCP23009_LOGIC_HIGH:
        sleep_ms(10)

    start = ticks_ms()

    while mcp.get_level(pin_number) == MCP23009_LOGIC_LOW:
        sleep_ms(10)

    end = ticks_ms()
    return ticks_diff(end, start)


print("=================================")
print("Morse Code Input")
print("=================================\n")
print("RIGHT short = dot")
print("RIGHT long  = dash")
print("LEFT        = validate letter")
print("UP          = space")
print("DOWN        = clear current symbol")
print()

while True:
    if mcp.get_level(DOT_DASH_PIN) == MCP23009_LOGIC_LOW:
        duration = wait_press_and_release(DOT_DASH_PIN)
        if duration >= LONG_PRESS_MS:
            current_symbol += "-"
            print("Dash  ->", current_symbol)
        else:
            current_symbol += "."
            print("Dot   ->", current_symbol)

    elif mcp.get_level(VALIDATE_PIN) == MCP23009_LOGIC_LOW:
        wait_press_and_release(VALIDATE_PIN)
        letter = MORSE_TABLE.get(current_symbol, "?")
        decoded_text += letter
        print("Letter:", letter)
        print("Text  :", decoded_text)
        current_symbol = ""

    elif mcp.get_level(SPACE_PIN) == MCP23009_LOGIC_LOW:
        wait_press_and_release(SPACE_PIN)
        decoded_text += " "
        print("Text  :", decoded_text)

    elif mcp.get_level(CLEAR_PIN) == MCP23009_LOGIC_LOW:
        wait_press_and_release(CLEAR_PIN)
        current_symbol = ""
        print("Current symbol cleared")

    sleep_ms(10)
