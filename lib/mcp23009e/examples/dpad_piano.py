"""
D-PAD piano example using the MCP23009E and the board buzzer.

UP    -> C
RIGHT -> D
DOWN  -> E
LEFT  -> F

If two or more buttons are pressed at the same time, the higher octave is used.
MENU exits the piano mode.
"""

from time import sleep_ms, sleep_us, ticks_diff, ticks_ms

from machine import I2C, Pin
from mcp23009e import MCP23009E
from mcp23009e.const import *

SPEAKER = Pin("SPEAKER", Pin.OUT_PP)

# I2C and expander setup
i2c = I2C(1)
reset_expander = Pin("RST_EXPANDER", Pin.OUT)
mcp = MCP23009E(i2c, address=MCP23009_I2C_ADDR, reset_pin=reset_expander)

# D-PAD mapping
BUTTONS = {
    MCP23009_BTN_UP: "UP",
    MCP23009_BTN_RIGHT: "RIGHT",
    MCP23009_BTN_DOWN: "DOWN",
    MCP23009_BTN_LEFT: "LEFT",
}

# Optional MENU button if available on the board
MENU_BUTTON = None

# Low octave
NOTES_LOW = {
    "UP": 262,     # C4
    "RIGHT": 294,  # D4
    "DOWN": 330,   # E4
    "LEFT": 349,   # F4
}

# High octave
NOTES_HIGH = {
    "UP": 523,     # C5
    "RIGHT": 587,  # D5
    "DOWN": 659,   # E5
    "LEFT": 698,   # F5
}


def tone(pin, freq, duration_ms):
    """Generate a square wave on the buzzer pin."""
    if freq == 0:
        sleep_ms(duration_ms)
        return

    period_us = int(1_000_000 / freq)
    half_period = period_us // 2
    end_time = ticks_ms() + duration_ms

    while ticks_diff(end_time, ticks_ms()) > 0:
        pin.on()
        sleep_us(half_period)
        pin.off()
        sleep_us(half_period)


def setup_buttons():
    """Configure D-PAD buttons as inputs with pull-ups."""
    for pin_number in BUTTONS:
        mcp.setup(pin_number, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)

    if MENU_BUTTON is not None:
        mcp.setup(MENU_BUTTON, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)


def get_pressed_buttons():
    """Return a list of currently pressed D-PAD button names."""
    pressed = []

    for pin_number, name in BUTTONS.items():
        if mcp.get_level(pin_number) == MCP23009_LOGIC_LOW:
            pressed.append(name)

    return pressed


def wait_all_released():
    """Wait until all D-PAD buttons are released."""
    while True:
        if len(get_pressed_buttons()) == 0:
            return
        sleep_ms(20)


def select_frequency(pressed):
    """Pick the note frequency based on pressed buttons."""
    if not pressed:
        return 0, None

    first = pressed[0]

    if len(pressed) >= 2:
        return NOTES_HIGH[first], first
    return NOTES_LOW[first], first


def dpad_piano():
    """Main piano loop."""
    setup_buttons()

    print("=================================")
    print("D-PAD Piano")
    print("=================================")
    print()
    print("UP    -> C")
    print("RIGHT -> D")
    print("DOWN  -> E")
    print("LEFT  -> F")
    print("Two or more buttons -> higher octave")
    print("Ctrl+C to stop")
    print()

    last_note = None
    last_octave = None

    try:
        while True:
            pressed = get_pressed_buttons()

            if pressed:
                frequency, note_name = select_frequency(pressed)
                octave = "high" if len(pressed) >= 2 else "low"

                if note_name != last_note or octave != last_octave:
                    print("Playing:", note_name, "-", frequency, "Hz", "(" + octave + " octave)")
                    last_note = note_name
                    last_octave = octave

                tone(SPEAKER, frequency, 60)
            else:
                last_note = None
                last_octave = None
                sleep_ms(20)

    except KeyboardInterrupt:
        print("\nPiano stopped.")


dpad_piano()
