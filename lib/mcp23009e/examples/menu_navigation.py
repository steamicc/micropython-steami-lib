"""
Minimal menu navigation example using the MCP23009E D-PAD and SSD1327 OLED display.

UP/DOWN -> move in the menu
RIGHT   -> select
LEFT    -> go back
"""

from time import sleep_ms

import micropython
import ssd1327
from machine import I2C, SPI, Pin
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
from steami_screen import Screen, SSD1327Display

# Setup MCP23009E on I2C bus
i2c = I2C(1)
reset_expander = Pin("RST_EXPANDER", Pin.OUT)
mcp = MCP23009E(i2c, address=MCP23009_I2C_ADDR, reset_pin=reset_expander)

# Setup SSD1327 display on SPI bus
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")
display = SSD1327Display(ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs))
screen = Screen(display)

# D-PAD button mapping
BUTTONS = {
    MCP23009_BTN_UP: "UP",
    MCP23009_BTN_DOWN: "DOWN",
    MCP23009_BTN_LEFT: "LEFT",
    MCP23009_BTN_RIGHT: "RIGHT",
}

MENU_ITEMS = [
    ("Battery", 4.01, "V"),
    ("Press", 1013, "hPa"),
    ("Hum", 48.6, "%"),
]


def setup_buttons():
    for pin_number in BUTTONS:
        mcp.setup(pin_number, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)


@micropython.native
def is_any_pressed():
    for pin_number in BUTTONS:  # noqa: SIM110
        if mcp.get_level(pin_number) == MCP23009_LOGIC_LOW:
            return True
    return False


def wait_all_released():
    while is_any_pressed():
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


def draw_menu(selected_index):
    labels = [label for label, _, _ in MENU_ITEMS]
    screen.clear()
    screen.title("MENU")
    screen.menu(labels, selected=selected_index)
    screen.subtitle("R:OK", "L:Back")
    screen.show()


def draw_detail(selected_index):
    name, val, unit = MENU_ITEMS[selected_index]
    screen.clear()
    screen.title(name)
    screen.value(val, unit=unit)
    screen.subtitle("L:Back")
    screen.show()


def main():
    setup_buttons()

    selected_index = 0
    in_detail = False

    draw_menu(selected_index)

    while True:
        button = wait_for_button()

        if not in_detail:
            if button == "UP":
                selected_index = (selected_index - 1) % len(MENU_ITEMS)
                draw_menu(selected_index)

            elif button == "DOWN":
                selected_index = (selected_index + 1) % len(MENU_ITEMS)
                draw_menu(selected_index)

            elif button == "RIGHT":
                draw_detail(selected_index)
                in_detail = True

        else:
            if button == "LEFT":
                draw_menu(selected_index)
                in_detail = False


main()
