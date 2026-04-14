from time import sleep_ms, ticks_ms, ticks_diff

import ssd1327
import random
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

# setup screen
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")
display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)

#setup mcp23009e
i2c = I2C(1)
reset_expander = Pin("RST_EXPANDER", Pin.OUT)
mcp = MCP23009E(i2c, address=MCP23009_I2C_ADDR, reset_pin=reset_expander)

# D-PAD button mapping 
BUTTONS = {
    MCP23009_BTN_UP: "UP",
    MCP23009_BTN_DOWN: "DOWN",
    MCP23009_BTN_LEFT: "LEFT",
    MCP23009_BTN_RIGHT: "RIGHT",
}

ACTION = ["food", "play"]
NEED = ["play whith me", "i'm hungry"]

#position of button 
X0 = 35
ITEM_Y = 100
ITEM_SPACING = 14

def setup_buttons():
    """Configure all D-PAD buttons as inputs with pull-ups."""
    for pin_number in BUTTONS:
        mcp.setup(pin_number, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)


def wait_for_button():
    """Wait for a button press and return its name."""
    for pin_number, name in BUTTONS.items():
        if mcp.get_level(pin_number) == MCP23009_LOGIC_LOW:
            while mcp.get_level(pin_number) == MCP23009_LOGIC_LOW:
                sleep_ms(20)
            return name
    return None


def creat_screen(selected_index, life, need):
    """displays the screen"""
    display.fill(0)
    display.text("life {}".format(life),28, 10)
    display.text(need, 15, 20)

    for index, label in enumerate(ACTION):
        y = ITEM_Y + index * ITEM_SPACING
        prefix = ">" if index == selected_index else " "
        display.text(prefix + label, X0, y, 15)

    display.show()


def action_check(selected_index, need,win):
    name = ACTION[selected_index]
    if need == "play whith me" and name == "play":
        win = True
        return win
    if need == "i'm hungry" and name == "food": 
        win = True
        return win
    else :
        win = False
        return win


def main(): 
    setup_buttons()

    selected_index = 0
    life = 100
    is_alive = True

    while is_alive:
        need = random.choice(NEED)
        creat_screen(selected_index, life, need)

        start = ticks_ms()
        win = False
        make_action = False

        while True:
            timer = ticks_diff(ticks_ms(), start)
            if timer >= 5000:
                break   

            button = wait_for_button()
            if button == "UP": 
                selected_index = (selected_index - 1)% len(ACTION)
                creat_screen(selected_index, life, need)
            elif button == "DOWN": 
                selected_index = (selected_index + 1) % len(ACTION)
                creat_screen(selected_index, life, need)
            elif button == "LEFT": 
                win = action_check(selected_index, need, win)
                make_action = True
                break 
            sleep_ms(20)

        if win: 
            need = random.choice(NEED)
            creat_screen(selected_index, life, need)
            sleep_ms(1000)
        else:
            life = max(0, life - 10)
            need = random.choice(NEED)
            creat_screen(selected_index, life, need)
            sleep_ms(1000)

        if life == 0:
            is_alive = False

main()
