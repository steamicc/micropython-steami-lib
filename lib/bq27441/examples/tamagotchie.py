import random
from time import sleep_ms, ticks_diff, ticks_ms

import ssd1327
from bq27441 import BQ27441
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
from pyb import Timer

# setup screen
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")
display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)

# setup mcp23009e
i2c = I2C(1)
reset_expander = Pin("RST_EXPANDER", Pin.OUT)
mcp = MCP23009E(i2c, address=MCP23009_I2C_ADDR, reset_pin=reset_expander)

# setup battery
fg = BQ27441(i2c)

# sound
buzzer_tim = Timer(1, freq=1000)
buzzer_ch  = buzzer_tim.channel(4, Timer.PWM, pin=Pin("SPEAKER"))
buzzer_ch.pulse_width_percent(0)

# D-PAD button mapping
BUTTONS = {
    MCP23009_BTN_UP: "UP",
    MCP23009_BTN_DOWN: "DOWN",
    MCP23009_BTN_LEFT: "LEFT",
    MCP23009_BTN_RIGHT: "RIGHT",
}

ACTION = ["food", "play"]
NEED = ["I'm bored", "i'm hungry"]

# position of button
X0 = 35
ITEM_Y = 100
ITEM_SPACING = 14

# sprite

SPRITE_BASE = [
    [0, 0, 15, 15, 0, 0, 0, 0, 0, 15, 15, 0, 0],
    [0, 15, 15, 15, 15, 0, 0, 0, 15, 15, 15, 15, 0],
    [0, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 0],
    [0, 15, 15, 0, 0, 0, 0, 0, 0, 0,15,15, 0],
    [0, 15, 0, 0, 15, 0, 0, 0, 15, 0, 0, 15, 0],
    [ 15, 0, 0, 0, 0, 15, 15, 15, 0, 0, 0, 0, 15],
    [15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15],
    [0, 15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15, 0],
    [15, 0, 0, 15, 0, 0, 0, 0, 0, 15, 0, 15, 0],
    [0, 15, 15, 0, 0, 0, 0, 0, 0, 15, 15, 15, 0],
    [0, 15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15, 0],
    [0, 0, 15, 0, 0, 0, 0, 0, 0, 0, 15, 0, 0],
    [0, 0, 0, 15, 0, 15, 15, 15, 0, 15, 0, 0, 0],
    [0, 0, 0,15, 0, 15, 0, 15, 0, 15, 0, 0, 0],
    [0, 0, 0, 0, 15, 0, 0, 0, 15, 0, 0, 0, 0],
]

SPRITE_HUNGRY = [
    [0, 0, 15, 15, 0, 0, 0, 0, 0, 15, 15, 0, 0],
    [0, 15, 15, 15, 15, 0, 0, 0, 15, 15, 15, 15, 0],
    [0, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 0],
    [0, 15, 15, 0, 0, 0, 0, 0, 0, 0, 15, 15, 0],
    [0, 15, 0, 0, 15, 0, 0, 0, 15, 0, 0, 15, 0],
    [15, 0, 0, 0, 0, 15, 15, 15, 0, 0, 0, 0, 15],
    [15, 0, 0, 0, 0, 15, 15, 15, 0, 0, 0, 0, 15],
    [0, 15, 0, 0, 0, 15, 15, 15, 0, 0, 0, 15, 0],
    [15, 0, 0, 15, 0, 0, 0, 0, 0, 15, 0, 15, 0],
    [0, 15, 15, 0, 0, 0, 0, 0, 0, 15, 15, 15, 0],
    [0, 15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15, 0],
    [0, 0, 15, 0, 0, 0, 0, 0, 0, 0, 15, 0, 0],
    [0, 0, 0, 15, 0, 15, 15, 15, 0, 15, 0, 0, 0],
    [0, 0, 0, 15, 0, 15, 0, 15, 0, 15, 0, 0, 0],
    [0, 0, 0, 0, 15, 0, 0, 0, 15, 0, 0, 0, 0],
]

SPRITE_SAD = [
    [0, 0, 15, 15, 0, 0, 0, 0, 0, 15, 15, 0, 0],
    [0, 15, 15, 15, 15, 0, 0, 0, 15, 15, 15, 15, 0],
    [0, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 0],
    [0, 15, 15, 0, 0, 0, 0, 0, 0, 0, 15, 15, 0],
    [0, 15, 0, 15, 15, 0, 0, 0, 15, 15, 0, 15, 0],
    [15, 0, 0, 0, 0, 0, 15, 0, 0, 0, 0, 0, 15],
    [15, 0, 0, 0, 0, 15, 0, 15, 0, 0, 0, 0, 15],
    [0, 15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15, 0],
    [15, 0, 0, 15, 0, 0, 0, 0, 0, 15, 0, 15, 0],
    [0, 15, 15, 0, 0, 0, 0, 0, 0, 15, 15, 15, 0],
    [0, 15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15, 0],
    [0, 0, 15, 0, 0, 0, 0, 0, 0, 0, 15, 0, 0],
    [0, 0, 0, 15, 0, 15, 15, 15, 0, 15, 0, 0, 0],
    [0, 0, 0, 15, 0, 15, 0, 15, 0, 15, 0, 0, 0],
    [0, 0, 0, 0, 15, 0, 0, 0, 15, 0, 0, 0, 0],
]

SPRITE_HAPPY = [
    [0, 0, 15, 15, 0, 0, 0, 0, 0, 15, 15, 0, 0],
    [0, 15, 15, 15, 15, 0, 0, 0, 15, 15, 15, 15, 0],
    [0, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 0],
    [0, 15, 15, 0, 0, 0, 0, 0, 0, 0, 15, 15, 0],
    [0, 15, 0, 0, 15, 0, 0, 0, 15, 0, 0, 15, 0],
    [15, 0, 0, 15, 0, 15, 0, 15, 0, 15, 0, 0, 15],
    [15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15],
    [0, 15, 0, 0, 0, 15, 15, 15, 0, 0, 0, 15, 0],
    [15, 0, 0, 15, 0, 0, 0, 0, 0, 15, 0, 15, 0],
    [0, 15, 15, 0, 0, 0, 0, 0, 0, 15, 15, 15, 0],
    [0, 15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15, 0],
    [0, 0, 15, 0, 0, 0, 0, 0, 0, 0, 15, 0, 0],
    [0, 0, 0, 15, 0, 15, 15, 15, 0, 15, 0, 0, 0],
    [0, 0, 0, 15, 0, 15, 0, 15, 0, 15, 0, 0, 0],
    [0, 0, 0, 0, 15, 0, 0, 0, 15, 0, 0, 0, 0],
]

SPRITE_HANGRY = [
    [0, 0, 15, 15, 0, 0, 0, 0, 0, 15, 15, 0, 0],
    [0, 15, 15, 15, 15, 0, 0, 0, 15, 15, 15, 15, 0],
    [0, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 0],
    [0, 15, 15, 0, 0, 0, 0, 0, 0, 0, 15, 15, 0],
    [0, 15, 0, 15, 0, 0, 0, 0, 0, 15, 0, 15, 0],
    [15, 0, 0, 0, 15, 0, 0, 0, 15, 0, 0, 0, 15],
    [15, 0, 0, 0, 0, 0, 15, 0, 0, 0, 0, 0, 15],
    [0, 15, 0, 0, 0, 15, 0, 15, 0, 0, 0, 15, 0],
    [15, 0, 0, 15, 0, 0, 0, 0, 0, 15, 0, 15, 0],
    [0, 15, 15, 0, 0, 0, 0, 0, 0, 15, 15, 15, 0],
    [0, 15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15, 0],
    [0, 0, 15, 0, 0, 0, 0, 0, 0, 0, 15, 0, 0],
    [0, 0, 0, 15, 0, 15, 15, 15, 0, 15, 0, 0, 0],
    [0, 0, 0, 15, 0, 15, 0, 15, 0, 15, 0, 0, 0],
    [0, 0, 0, 0, 15, 0, 0, 0, 15, 0, 0, 0, 0],
]

SPRITE_DEAD = [
    [0, 0, 0, 0, 0, 0, 15, 15, 15, 15, 15, 15, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 15, 15, 0, 0, 0, 0, 0, 0, 15, 15, 0, 0, 0],
    [0, 0, 0, 15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15, 0, 0],
    [0, 0, 15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15, 0],
    [0, 0, 15, 0, 0, 0, 0, 0, 0, 0, 0, 15, 0, 15, 0, 15, 0],
    [0, 15, 0, 0, 15, 15, 0, 0, 0, 0, 0, 15, 0, 15, 0, 0, 15],
    [0, 15, 0, 15, 0, 0, 15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15],
    [0, 15, 0, 15, 0, 0, 0, 0, 0, 0, 15, 0, 15, 0, 15, 0, 15],
    [15, 0, 0, 0, 15, 0, 0, 0, 0, 0, 15, 15, 15, 15, 15, 0, 15],
    [15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15, 15, 15, 15, 15, 0, 15],
    [15, 0, 0, 0, 0, 0, 0, 0, 0, 15, 15, 15, 15, 15, 0, 15, 0],
    [0, 15, 0, 0, 0, 0, 0, 0, 0, 15, 0, 15, 0, 15, 0, 15, 0],
    [0, 0, 15, 15, 15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15, 0, 0],
    [0, 0, 0, 0, 0, 15, 15, 0, 0, 0, 0, 15, 15, 15, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 15, 15, 15, 15, 0, 0, 0, 0, 0, 0],
]

SOUND = {
        "start": [
        (523,  120),
        (659,  120),
        (784,  120),
        (1047, 400),
        ],

        "hungry": [
            (400, 150),
            (350, 150),
            (300, 300),
        ],

        "bored": [
            (500, 120),
            (650, 120),
            (800, 200),
        ],

        "success": [
            (600, 100),
            (800, 100),
            (1000, 200),
        ],

        "evolution": [
            (600, 120),
            (750, 120),
            (900, 120),
            (1100, 150),
            (1300, 300),
        ],

        "fail": [
            (500, 150),
            (400, 150),
            (300, 400),
        ]
    }

# ------------------------------------SCREEN----------------------------------------------

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
    """Draw character"""
    fb = display.framebuf
    for y, row in enumerate(sprite):
        for x, color in enumerate(row):
            for dy in range(scale):
                for dx in range(scale):
                    fb.pixel(cx + x*scale + dx, cy + y*scale + dy, color)


def create_screen(selected_index, need, sprite, charge):
    """displays the screen"""
    display.fill(0)
    display.text(need, 25, 20)
    display.text(str(charge), 50, 10)

    if charge > 70 :
        scale = 1
        x = 55
        y = 60
    elif charge < 70 and charge > 40 :
        scale = 2
        x = 45
        y = 50
    else :
        scale = 3
        x = 40
        y = 40

    draw_character(x, y, scale, sprite)

    for index, label in enumerate(ACTION):
        y = ITEM_Y + index * ITEM_SPACING
        prefix = ">" if index == selected_index else " "
        display.text(prefix + label, X0, y, 15)

    display.show()

def create_game_over_screen():
    display.fill(0)
    display.text("Game-Over",25, 20)
    draw_character(35, 45, 3, SPRITE_DEAD)
    display.show()
# ------------------------------------gameplay----------------------------------------------

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

def sound_effect(name):
    melody = SOUND[name]
    for freq, duration_ms in melody:
        buzzer_tim.freq(freq)
        buzzer_ch.pulse_width_percent(10)
        sleep_ms(duration_ms)
        buzzer_ch.pulse_width_percent(0)
        sleep_ms(30)


# ------------------------------------main----------------------------------------------

def main():
    setup_buttons()
    sound_effect("start")
    is_alive = True

    try:
        while is_alive:
            selected_index = 0
            charge = fg.state_of_charge()

            need = " "
            create_screen(selected_index, need, SPRITE_BASE, charge)
            sleep_ms(1000)

            need = random.choice(NEED)
            if need == "I'm bored" :
                sprite = SPRITE_SAD
                sound_effect("bored")
            else :
                sprite = SPRITE_HUNGRY
                sound_effect("hungry")

            create_screen(selected_index, need, sprite, charge)

            start = ticks_ms()
            win = None

            while True:
                timer = ticks_diff(ticks_ms(), start)
                if timer >= 5000:
                    break


                button = wait_for_button()
                if button == "UP":
                    selected_index = (selected_index - 1)% len(ACTION)
                    create_screen(selected_index, need, sprite, charge)
                elif button == "DOWN":
                    selected_index = (selected_index + 1) % len(ACTION)
                    create_screen(selected_index, need, sprite, charge)
                elif button == "LEFT":
                    win = action_check(selected_index, need, win)
                    break
                sleep_ms(20)

            if win:
                create_screen(selected_index, need, SPRITE_HAPPY, charge)
                sound_effect("success")
            else:
                create_screen(selected_index, need, SPRITE_HANGRY, charge)
                sound_effect("fail")
            sleep_ms(1000)

            if charge < 10:
                is_alive = False
                create_game_over_screen()
    finally:
        buzzer_ch.pulse_width_percent(0)
main()
