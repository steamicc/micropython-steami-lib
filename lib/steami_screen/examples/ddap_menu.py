"""
Displays a scrollable menu navigated with the D-pad buttons.
"""

from time import sleep_ms

from machine import I2C, Pin
from mcp23009e import MCP23009E
from mcp23009e.const import (
    MCP23009_BTN_DOWN,
    MCP23009_BTN_UP,
    MCP23009_DIR_INPUT,
    MCP23009_I2C_ADDR,
    MCP23009_LOGIC_LOW,
    MCP23009_PULLUP,
)
from steami import Screen

# --- Screen setup ---
screen = Screen()
screen.begin()  # allocate the frame buffer early in the program

# --- D-pad setup ---
i2c = I2C(1)

reset = Pin("RST_EXPANDER", Pin.OUT)
mcp = MCP23009E(i2c, address=MCP23009_I2C_ADDR, reset_pin=reset)

mcp.setup(MCP23009_BTN_UP, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)
mcp.setup(MCP23009_BTN_DOWN, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)

# --- Menu items ---
items = ["Temperature", "Humidity", "Distance", "Light", "Battery", "Proximity"]
selected = 0

# --- Main loop ---
while True:
    if mcp.get_level(MCP23009_BTN_UP) == MCP23009_LOGIC_LOW:
        selected = (selected - 1) % len(items)
        sleep_ms(200)

    if mcp.get_level(MCP23009_BTN_DOWN) == MCP23009_LOGIC_LOW:
        selected = (selected + 1) % len(items)
        sleep_ms(200)

    screen.clear()
    screen.title("Menu")
    screen.menu(items, selected=selected)
    screen.show()

    sleep_ms(50)
