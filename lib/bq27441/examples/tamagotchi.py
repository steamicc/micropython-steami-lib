"""Battery Tamagotchi example using BQ27441, MCP23009E D-PAD, SSD1327 OLED and buzzer.

The creature ages based on the real battery percentage and periodically asks
to be fed or played with via the D-PAD. A correct answer triggers a happy
sprite + success sound; a wrong or missed answer triggers an angry sprite +
fail sound. When the battery drops below 10 %, the game is over.

Controls:
    UP / DOWN  -> navigate the action menu
    LEFT       -> confirm selection
"""

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

# --- Hardware setup ---

spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")
display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)

i2c = I2C(1)
reset_expander = Pin("RST_EXPANDER", Pin.OUT)
mcp = MCP23009E(i2c, address=MCP23009_I2C_ADDR, reset_pin=reset_expander)

fg = BQ27441(i2c)

buzzer_tim = Timer(1, freq=1000)
buzzer_ch = buzzer_tim.channel(4, Timer.PWM, pin=Pin("SPEAKER"))
buzzer_ch.pulse_width_percent(0)

# --- Constants ---

BUTTONS = {
    MCP23009_BTN_UP: "UP",
    MCP23009_BTN_DOWN: "DOWN",
    MCP23009_BTN_LEFT: "LEFT",
    MCP23009_BTN_RIGHT: "RIGHT",
}

ACTION = ["food", "play"]
NEED = ["I'm bored", "I'm hungry"]

IDLE_DISPLAY_MS = 1000
RESPONSE_TIMEOUT_MS = 5000
RESULT_DISPLAY_MS = 1000

X0 = 35
ITEM_Y = 100
ITEM_SPACING = 14

# --- Sprites ---

SPRITE_BASE = [
    [0, 0, 15, 15, 0, 0, 0, 0, 0, 15, 15, 0, 0],
    [0, 15, 15, 15, 15, 0, 0, 0, 15, 15, 15, 15, 0],
    [0, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 0],
    [0, 15, 15, 0, 0, 0, 0, 0, 0, 0, 15, 15, 0],
    [0, 15, 0, 0, 15, 0, 0, 0, 15, 0, 0, 15, 0],
    [15, 0, 0, 0, 0, 15, 15, 15, 0, 0, 0, 0, 15],
    [15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15],
    [0, 15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15, 0],
    [15, 0, 0, 15, 0, 0, 0, 0, 0, 15, 0, 15, 0],
    [0, 15, 15, 0, 0, 0, 0, 0, 0, 15, 15, 15, 0],
    [0, 15, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15, 0],
    [0, 0, 15, 0, 0, 0, 0, 0, 0, 0, 15, 0, 0],
    [0, 0, 0, 15, 0, 15, 15, 15, 0, 15, 0, 0, 0],
    [0, 0, 0, 15, 0, 15, 0, 15, 0, 15, 0, 0, 0],
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

SPRITE_ANGRY = [
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

# --- Sounds ---

SOUND = {
    "start": [
        (523, 120),
        (659, 120),
        (784, 120),
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
    "fail": [
        (500, 150),
        (400, 150),
        (300, 400),
    ],
}

# --- Helpers ---


def setup_buttons():
    """Configure all D-PAD buttons as inputs with pull-ups."""
    for pin_number in BUTTONS:
        mcp.setup(pin_number, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)


def wait_for_button():
    """Poll D-PAD once and return the pressed button name, or None."""
    for pin_number, name in BUTTONS.items():
        if mcp.get_level(pin_number) == MCP23009_LOGIC_LOW:
            while mcp.get_level(pin_number) == MCP23009_LOGIC_LOW:
                sleep_ms(20)
            return name
    return None


def draw_character(cx, cy, scale, sprite):
    """Draw a scaled pixel-art sprite on the display framebuf."""
    fb = display.framebuf
    for y, row in enumerate(sprite):
        for x, color in enumerate(row):
            for dy in range(scale):
                for dx in range(scale):
                    fb.pixel(cx + x * scale + dx, cy + y * scale + dy, color)


def create_screen(selected_index, need, sprite, charge):
    """Render one game frame: sprite, need text, charge and action menu."""
    display.fill(0)
    display.text(need, 25, 20, 15)
    display.text(str(charge), 50, 10, 15)

    if charge >= 70:
        scale, x, y = 1, 55, 60
    elif charge >= 40:
        scale, x, y = 2, 45, 50
    else:
        scale, x, y = 3, 40, 40

    draw_character(x, y, scale, sprite)

    for index, label in enumerate(ACTION):
        row_y = ITEM_Y + index * ITEM_SPACING
        prefix = ">" if index == selected_index else " "
        display.text(prefix + label, X0, row_y, 15)

    display.show()


def create_game_over_screen():
    """Display the game-over screen."""
    display.fill(0)
    display.text("Game Over", 25, 20, 15)
    draw_character(35, 45, 3, SPRITE_DEAD)
    display.show()


def action_check(selected_index, need):
    """Check if the selected action matches the current need."""
    name = ACTION[selected_index]
    return (need == "I'm bored" and name == "play") or (need == "I'm hungry" and name == "food")


def sound_effect(name):
    """Play a short melody from the SOUND dictionary."""
    for freq, duration_ms in SOUND[name]:
        buzzer_tim.freq(freq)
        buzzer_ch.pulse_width_percent(10)
        sleep_ms(duration_ms)
        buzzer_ch.pulse_width_percent(0)
        sleep_ms(30)


# --- Main game loop ---


def main():
    """Run the Tamagotchi game."""
    setup_buttons()
    sound_effect("start")
    is_alive = True

    try:
        while is_alive:
            selected_index = 0
            charge = fg.state_of_charge()

            # Idle phase
            create_screen(selected_index, " ", SPRITE_BASE, charge)
            sleep_ms(IDLE_DISPLAY_MS)

            # Need phase
            need = random.choice(NEED)
            if need == "I'm bored":
                sprite = SPRITE_SAD
                sound_effect("bored")
            else:
                sprite = SPRITE_HUNGRY
                sound_effect("hungry")

            create_screen(selected_index, need, sprite, charge)

            # Response phase
            start = ticks_ms()
            win = None

            while True:
                elapsed = ticks_diff(ticks_ms(), start)
                if elapsed >= RESPONSE_TIMEOUT_MS:
                    break

                button = wait_for_button()
                if button == "UP":
                    selected_index = (selected_index - 1) % len(ACTION)
                    create_screen(selected_index, need, sprite, charge)
                elif button == "DOWN":
                    selected_index = (selected_index + 1) % len(ACTION)
                    create_screen(selected_index, need, sprite, charge)
                elif button == "LEFT":
                    win = action_check(selected_index, need)
                    break
                sleep_ms(20)

            # Result phase
            if win:
                create_screen(selected_index, need, SPRITE_HAPPY, charge)
                sound_effect("success")
            else:
                create_screen(selected_index, need, SPRITE_ANGRY, charge)
                sound_effect("fail")
            sleep_ms(RESULT_DISPLAY_MS)

            if charge < 10:
                is_alive = False
                create_game_over_screen()
    finally:
        buzzer_ch.pulse_width_percent(0)


main()
