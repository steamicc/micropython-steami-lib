"""
Minimal menu navigation example using the MCP23009E D-PAD and SSD1327 OLED display.

UP/DOWN -> move in the menu
RIGHT   -> select
LEFT    -> go back

The UI stays in the center of the round display to avoid cropped corners.
"""

from time import sleep_ms

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

# Setup MCP23009E on I2C bus
i2c = I2C(1)
reset_expander = Pin("RST_EXPANDER", Pin.OUT)
mcp = MCP23009E(i2c, address=MCP23009_I2C_ADDR, reset_pin=reset_expander)

# Setup SSD1327 display on SPI bus
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")
display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)

# D-PAD button mapping
BUTTONS = {
    MCP23009_BTN_UP: "UP",
    MCP23009_BTN_DOWN: "DOWN",
    MCP23009_BTN_LEFT: "LEFT",
    MCP23009_BTN_RIGHT: "RIGHT",
}

# Keep short labels for a compact centered UI
MENU_ITEMS = [
    ("Battery", "4.01 V"),
    ("Press", "1013 hPa"),
    ("Hum", "48.6 %"),
]

# Central safe area for the round display
X0 = 28
TITLE_Y = 28
ITEM_Y = 46
ITEM_SPACING = 14
FOOTER_Y = 92


def setup_buttons():
    """Configure all D-PAD buttons as inputs with pull-ups."""
    for pin_number in BUTTONS:
        mcp.setup(pin_number, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)


def wait_all_released():
    """Wait until all buttons are released."""
    while True:
        all_released = True
        for pin_number in BUTTONS:
            if mcp.get_level(pin_number) == MCP23009_LOGIC_LOW:
                all_released = False
                break
        if all_released:
            return
        sleep_ms(20)


def wait_for_button():
    """Wait for a button press and return its name."""
    wait_all_released()

    while True:
        for pin_number, name in BUTTONS.items():
            if mcp.get_level(pin_number) == MCP23009_LOGIC_LOW:
                while mcp.get_level(pin_number) == MCP23009_LOGIC_LOW:
                    sleep_ms(20)
                return name
        sleep_ms(20)


def draw_menu(selected_index):
    """Draw the centered menu."""
    display.fill(0)

    display.text("MENU", 48, TITLE_Y, 15)

    for index, (label, _) in enumerate(MENU_ITEMS):
        y = ITEM_Y + index * ITEM_SPACING
        prefix = ">" if index == selected_index else " "
        display.text(prefix + label, X0, y, 15)

    display.text("R:OK  L:BACK", 24, FOOTER_Y, 8)
    display.show()


def draw_detail(selected_index):
    """Draw the centered detail screen."""
    name, value = MENU_ITEMS[selected_index]

    display.fill(0)

    display.text(name, 44, 34, 15)
    display.text(value, 34, 56, 15)
    display.text("LEFT BACK", 34, 88, 8)

    display.show()


def main():
    """Main UI loop."""
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
