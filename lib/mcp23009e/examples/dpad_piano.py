"""
D-PAD piano example using the MCP23009E and the board buzzer.

UP    -> C
RIGHT -> D
DOWN  -> E
LEFT  -> F

If two or more buttons are pressed at the same time, the higher octave is used.
MENU exits the piano mode.
"""

from time import sleep_ms

from machine import I2C, Pin
from mcp23009e import MCP23009E
from mcp23009e.const import *
from pyb import Timer

# Board pins
MENU_BUTTON = Pin("MENU_BUTTON", Pin.IN, Pin.PULL_UP)

# Hardware PWM on SPEAKER pin (PA11 = TIM1_CH4)
buzzer_tim = Timer(1, freq=1000)
buzzer_ch = buzzer_tim.channel(4, Timer.PWM, pin=Pin("SPEAKER"))
buzzer_ch.pulse_width_percent(0)

# I2C and expander setup
i2c = I2C(1)
reset_expander = Pin("RST_EXPANDER", Pin.OUT)
mcp = MCP23009E(i2c, address=MCP23009_I2C_ADDR, reset_pin=reset_expander)

# D-PAD mapping on the MCP23009E
BUTTONS = {
    MCP23009_BTN_UP: "UP",
    MCP23009_BTN_RIGHT: "RIGHT",
    MCP23009_BTN_DOWN: "DOWN",
    MCP23009_BTN_LEFT: "LEFT",
}

# Low octave notes
NOTES_LOW = {
    "UP": 262,     # C4
    "RIGHT": 294,  # D4
    "DOWN": 330,   # E4
    "LEFT": 349,   # F4
}

# High octave notes
NOTES_HIGH = {
    "UP": 523,     # C5
    "RIGHT": 587,  # D5
    "DOWN": 659,   # E5
    "LEFT": 698,   # F5
}


def tone(freq):
    """Start a tone using hardware PWM."""
    if freq <= 0:
        no_tone()
        return
    buzzer_tim.freq(freq)
    buzzer_ch.pulse_width_percent(50)


def no_tone():
    """Silence the buzzer."""
    buzzer_ch.pulse_width_percent(0)


def setup_buttons():
    """Configure D-PAD buttons as MCP23009E inputs with pull-ups."""
    for pin_number in BUTTONS:
        mcp.setup(pin_number, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)


def get_pressed_buttons():
    """Return a list of currently pressed D-PAD button names."""
    pressed = []

    for pin_number, name in BUTTONS.items():
        if mcp.get_level(pin_number) == MCP23009_LOGIC_LOW:
            pressed.append(name)

    return pressed


def select_frequency(pressed):
    """Select the note frequency from the current pressed buttons."""
    if not pressed:
        return 0, None, None

    note_name = pressed[0]

    if len(pressed) >= 2:
        return NOTES_HIGH[note_name], note_name, "high"

    return NOTES_LOW[note_name], note_name, "low"


def wait_menu_release():
    """Wait until the MENU button is released."""
    while MENU_BUTTON.value() == 0:
        sleep_ms(20)


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
    print("MENU  -> exit")
    print()

    last_note = None
    last_octave = None
    last_freq = 0

    try:
        while True:
            if MENU_BUTTON.value() == 0:
                print("Menu button pressed, exiting piano.")
                wait_menu_release()
                break

            pressed = get_pressed_buttons()
            frequency, note_name, octave = select_frequency(pressed)

            if frequency == 0:
                if last_freq != 0:
                    no_tone()
                last_note = None
                last_octave = None
                last_freq = 0
                sleep_ms(20)
                continue

            if note_name != last_note or octave != last_octave:
                print(
                    "Playing:",
                    note_name,
                    "-",
                    frequency,
                    "Hz",
                    "(" + octave + " octave)",
                )
                tone(frequency)
                last_note = note_name
                last_octave = octave
                last_freq = frequency

            sleep_ms(20)

    except KeyboardInterrupt:
        print("\nPiano stopped.")
    finally:
        no_tone()


dpad_piano()
