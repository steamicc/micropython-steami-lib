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
NEED = ["I'm bored", "i'm hungry"]

#position of button 
X0 = 35
ITEM_Y = 100
ITEM_SPACING = 14

SPRITE_BASE = [
    [ 0, 0,15,15, 0, 0, 0, 0, 0,15,15, 0, 0],
    [ 0,15,15,15,15, 0, 0, 0,15,15,15,15, 0],
    [ 0,15,15,15,15,15,15,15,15,15,15,15, 0],
    [ 0,15,15, 0, 0, 0, 0, 0, 0, 0,15,15, 0],
    [ 0,15, 0, 0,15, 0, 0, 0,15, 0, 0,15, 0],
    [15, 0, 0, 0, 0,15,15,15, 0, 0, 0, 0,15],
    [15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15],
    [ 0,15, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0],
    [15, 0, 0,15, 0, 0, 0, 0, 0,15, 0,15, 0],
    [ 0,15,15, 0, 0, 0, 0, 0, 0,15,15,15, 0],
    [ 0,15, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0],
    [ 0, 0,15, 0, 0, 0, 0, 0, 0, 0,15, 0, 0],
    [ 0, 0, 0,15, 0,15,15,15, 0,15, 0, 0, 0],
    [ 0, 0, 0,15, 0,15, 0,15, 0,15, 0, 0, 0],
    [ 0, 0, 0, 0,15, 0, 0, 0,15, 0, 0, 0, 0],
]

SPRITE_HUNGRY = [
    [ 0, 0,15,15, 0, 0, 0, 0, 0,15,15, 0, 0],
    [ 0,15,15,15,15, 0, 0, 0,15,15,15,15, 0],
    [ 0,15,15,15,15,15,15,15,15,15,15,15, 0],
    [ 0,15,15, 0, 0, 0, 0, 0, 0, 0,15,15, 0],
    [ 0,15, 0, 0,15, 0, 0, 0,15, 0, 0,15, 0],
    [15, 0, 0, 0, 0,15,15,15, 0, 0, 0, 0,15],
    [15, 0, 0, 0, 0,15,15,15, 0, 0, 0, 0,15],
    [ 0,15, 0, 0, 0,15,15,15, 0, 0, 0,15, 0],
    [15, 0, 0,15, 0, 0, 0, 0, 0,15, 0,15, 0],
    [ 0,15,15, 0, 0, 0, 0, 0, 0,15,15,15, 0],
    [ 0,15, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0],
    [ 0, 0,15, 0, 0, 0, 0, 0, 0, 0,15, 0, 0],
    [ 0, 0, 0,15, 0,15,15,15, 0,15, 0, 0, 0],
    [ 0, 0, 0,15, 0,15, 0,15, 0,15, 0, 0, 0],
    [ 0, 0, 0, 0,15, 0, 0, 0,15, 0, 0, 0, 0],
]

SPRITE_SAD = [
    [ 0, 0,15,15, 0, 0, 0, 0, 0,15,15, 0, 0],
    [ 0,15,15,15,15, 0, 0, 0,15,15,15,15, 0],
    [ 0,15,15,15,15,15,15,15,15,15,15,15, 0],
    [ 0,15,15, 0, 0, 0, 0, 0, 0, 0,15,15, 0],
    [ 0,15, 0,15,15, 0, 0, 0,15,15, 0,15, 0],
    [15, 0, 0, 0, 0, 0,15, 0, 0, 0, 0, 0,15],
    [15, 0, 0, 0, 0,15, 0,15, 0, 0, 0, 0,15],
    [ 0,15, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0],
    [15, 0, 0,15, 0, 0, 0, 0, 0,15, 0,15, 0],
    [ 0,15,15, 0, 0, 0, 0, 0, 0,15,15,15, 0],
    [ 0,15, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0],
    [ 0, 0,15, 0, 0, 0, 0, 0, 0, 0,15, 0, 0],
    [ 0, 0, 0,15, 0,15,15,15, 0,15, 0, 0, 0],
    [ 0, 0, 0,15, 0,15, 0,15, 0,15, 0, 0, 0],
    [ 0, 0, 0, 0,15, 0, 0, 0,15, 0, 0, 0, 0],
]

SPRITE_HAPPY = [
    [ 0, 0,15,15, 0, 0, 0, 0, 0,15,15, 0, 0],
    [ 0,15,15,15,15, 0, 0, 0,15,15,15,15, 0],
    [ 0,15,15,15,15,15,15,15,15,15,15,15, 0],
    [ 0,15,15, 0, 0, 0, 0, 0, 0, 0,15,15, 0],
    [ 0,15, 0, 0,15, 0, 0, 0,15, 0, 0,15, 0],
    [15, 0, 0,15, 0,15, 0,15, 0,15, 0, 0,15],
    [15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15],
    [ 0,15, 0, 0, 0,15, 15,15, 0, 0, 0,15, 0],
    [15, 0, 0,15, 0, 0, 0, 0, 0,15, 0,15, 0],
    [ 0,15,15, 0, 0, 0, 0, 0, 0,15,15,15, 0],
    [ 0,15, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0],
    [ 0, 0,15, 0, 0, 0, 0, 0, 0, 0,15, 0, 0],
    [ 0, 0, 0,15, 0,15,15,15, 0,15, 0, 0, 0],
    [ 0, 0, 0,15, 0,15, 0,15, 0,15, 0, 0, 0],
    [ 0, 0, 0, 0,15, 0, 0, 0,15, 0, 0, 0, 0],
]

SPRITE_HANGRY = [
    [ 0, 0,15,15, 0, 0, 0, 0, 0,15,15, 0, 0],
    [ 0,15,15,15,15, 0, 0, 0,15,15,15,15, 0],
    [ 0,15,15,15,15,15,15,15,15,15,15,15, 0],
    [ 0,15,15, 0, 0, 0, 0, 0, 0, 0,15,15, 0],
    [ 0,15, 0,15, 0, 0, 0, 0, 0,15, 0,15, 0],
    [15, 0, 0, 0,15, 0, 0, 0,15, 0, 0, 0,15],
    [15, 0, 0, 0, 0, 0,15, 0, 0, 0, 0, 0,15],
    [ 0,15, 0, 0, 0,15, 0,15, 0, 0, 0,15, 0],
    [15, 0, 0,15, 0, 0, 0, 0, 0,15, 0,15, 0],
    [ 0,15,15, 0, 0, 0, 0, 0, 0,15,15,15, 0],
    [ 0,15, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0],
    [ 0, 0,15, 0, 0, 0, 0, 0, 0, 0,15, 0, 0],
    [ 0, 0, 0,15, 0,15,15,15, 0,15, 0, 0, 0],
    [ 0, 0, 0,15, 0,15, 0,15, 0,15, 0, 0, 0],
    [ 0, 0, 0, 0,15, 0, 0, 0,15, 0, 0, 0, 0],
]

SPRITE_DEAD = [
    [ 0, 0, 0, 0, 0, 0,15,15,15,15,15,15, 0, 0, 0, 0, 0],
    [ 0, 0, 0, 0,15,15, 0, 0, 0, 0, 0, 0,15,15, 0, 0, 0],
    [ 0, 0, 0,15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0, 0],
    [ 0, 0,15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0],
    [ 0, 0,15, 0, 0, 0, 0, 0, 0, 0, 0,15, 0,15, 0,15, 0],
    [ 0,15, 0, 0,15,15, 0, 0, 0, 0, 0,15, 0,15, 0, 0,15],
    [ 0,15, 0,15, 0, 0,15, 0, 0, 0, 0, 0, 0, 0, 0, 0,15],
    [ 0,15, 0,15, 0, 0, 0, 0, 0, 0,15, 0,15, 0,15, 0,15],
    [15, 0, 0, 0,15, 0, 0, 0, 0, 0,15,15,15,15,15, 0,15],
    [15, 0, 0, 0, 0, 0, 0, 0, 0, 0,15,15,15,15,15, 0,15],
    [15, 0, 0, 0, 0, 0, 0, 0, 0,15,15,15,15,15, 0,15, 0],
    [ 0,15, 0, 0, 0, 0, 0, 0, 0,15, 0,15, 0,15, 0,15, 0],
    [ 0, 0,15,15,15, 0, 0, 0, 0, 0, 0, 0, 0, 0,15, 0, 0],
    [ 0, 0, 0, 0, 0,15,15, 0, 0, 0, 0,15,15,15, 0, 0, 0],
    [ 0, 0, 0, 0, 0, 0, 0,15,15,15,15, 0, 0, 0, 0, 0, 0],
]

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

def draw_character(cx, cy, scale, sprite):
    """Draw caractere"""
    fb = display.framebuf
    for y, row in enumerate(sprite):
        for x, color in enumerate(row):
            for dy in range(scale):
                for dx in range(scale):
                    fb.pixel(cx + x*scale + dx, cy + y*scale + dy, color)
    
    
    
def creat_screen(selected_index, need, sprite):
    """displays the screen"""
    display.fill(0)
    display.text(need, 15, 20)

    draw_character(40, 40, 3, sprite)

    for index, label in enumerate(ACTION):
        y = ITEM_Y + index * ITEM_SPACING
        prefix = ">" if index == selected_index else " "
        display.text(prefix + label, X0, y, 15)

    display.show()


def action_check(selected_index, need,win):
    name = ACTION[selected_index]
    if need == "I'm bored" and name == "play":
        win = True
        return win
    if need == "i'm hungry" and name == "food": 
        win = True
        return win
    else :
        win = False
        return win

def creat_game_over_screen():
    display.fill(0)     
    display.text("Game-Over",25, 20)
    draw_character(35, 45, 3, SPRITE_DEAD)
    display.show()

def main():
    setup_buttons()

    selected_index = 0
    life = 30
    is_alive = True
    
    while is_alive:
        need = " "
        creat_screen(selected_index, need, SPRITE_BASE)
        sleep_ms(1000)

        need = random.choice(NEED)
        if need == "I'm bored" :
            sprite = SPRITE_SAD
        else :
            sprite = SPRITE_HUNGRY

        creat_screen(selected_index, need, sprite)

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
                creat_screen(selected_index, need, sprite)
            elif button == "DOWN": 
                selected_index = (selected_index + 1) % len(ACTION)
                creat_screen(selected_index, need, sprite)
            elif button == "LEFT": 
                win = action_check(selected_index, need, win)
                make_action = True
                break 
            sleep_ms(20)

        if win: 
            sleep_ms(1000)
            creat_screen(selected_index, need, SPRITE_HAPPY)
            sleep_ms(1000)
        else:
            life = max(-10, life - 10)
            creat_screen(selected_index, need, SPRITE_HANGRY)
            sleep_ms(1000)

        if life == 0:
            is_alive = False
            creat_game_over_screen()

main()
