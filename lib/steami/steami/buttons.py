from time import sleep_ms, ticks_diff, ticks_ms

from machine import Pin
from mcp23009e.const import (
    MCP23009_BTN_DOWN,
    MCP23009_BTN_LEFT,
    MCP23009_BTN_RIGHT,
    MCP23009_BTN_UP,
    MCP23009_DIR_INPUT,
    MCP23009_PULLUP,
)

from steami.const import DEBOUNCE_MS, POLL_MS, Function, Status
from steami.handle import Handle

# The buttons, in bit order of the state. A, B and MENU are MCU pins, active low.
_NAMES = ("A", "B", "MENU", "UP", "DOWN", "LEFT", "RIGHT")
_PINS = ("A_BUTTON", "B_BUTTON", "MENU_BUTTON")
# Expander bit of UP, DOWN, LEFT and RIGHT.
_DPAD_BITS = (MCP23009_BTN_UP, MCP23009_BTN_DOWN, MCP23009_BTN_LEFT, MCP23009_BTN_RIGHT)


def _setup_dpad(driver):
    for bit in _DPAD_BITS:
        driver.setup(bit, MCP23009_DIR_INPUT, MCP23009_PULLUP)


class Buttons(Handle):
    """The A, B and MENU buttons and the D-pad (UP, DOWN, LEFT, RIGHT).

    Buttons are named by text: "A", "B", "MENU", "UP", "DOWN", "LEFT", "RIGHT";
    any other name raises ValueError. A, B and MENU are MCU pins and always
    work. The D-pad is on the MCP23009E: when it does not answer, the D-pad
    reads as released. Creating it touches no hardware.

    Polling, no interrupts: the state moves only when a method is called, so
    call one on every loop turn. Debounce is 20 ms: a change is taken at once,
    then the bounces of the next 20 ms are ignored.
    """

    _NOUN = "D-PAD expander"
    _HINT = "The A, B and MENU buttons still work."
    _FALLBACK = "the D-PAD will read as released."

    def __init__(self):
        super().__init__(Function.BUTTONS)
        self._pins = None
        self._primed = False
        self._state = 0
        self._pressed = 0
        self._released = 0
        self._changed_at = [None] * len(_NAMES)  # None: free to change

    def begin(self):
        """Set the pins up and find the D-pad expander. True when it answered.

        A, B and MENU work whatever the answer.
        """
        if self._pins is None:
            self._pins = [Pin(name, Pin.IN, Pin.PULL_UP) for name in _PINS]
        if self._status != Status.NOT_STARTED:
            return super().begin()
        ok = super().begin()
        if ok:
            self._read(None, _setup_dpad)
        return ok

    def is_pressed(self, name):
        """True while the button is held (debounced)."""
        bit = _bit(name)
        self._sample()
        return (self._state & bit) != 0

    def was_pressed(self, name):
        """True once per press, since the last time it was asked."""
        bit = _bit(name)
        self._sample()
        found = (self._pressed & bit) != 0
        self._pressed &= ~bit
        return found

    def was_released(self, name):
        """True once per release, since the last time it was asked."""
        bit = _bit(name)
        self._sample()
        found = (self._released & bit) != 0
        self._released &= ~bit
        return found

    def wait_for_press(self, timeout_ms=None):
        """Wait for a new press and return the name of the button.

        Returns None after timeout_ms; with None, waits forever. Presses
        latched before the call are dropped.
        """
        self._pressed = 0
        start = ticks_ms()
        while True:
            self._sample()
            for i, name in enumerate(_NAMES):
                if self._pressed & (1 << i):
                    self._pressed &= ~(1 << i)
                    return name
            if timeout_ms is not None and ticks_diff(ticks_ms(), start) >= timeout_ms:
                return None
            sleep_ms(POLL_MS)

    def _sample(self):
        if self._status == Status.NOT_STARTED:
            self.begin()
        now = 0
        for i, pin in enumerate(self._pins):
            if pin.value() == 0:
                now |= 1 << i
        port = self._read(None, "get_gpio")  # on an error the D-pad reads released
        if port is not None:
            for i, bit in enumerate(_DPAD_BITS):
                if not port & (1 << bit):
                    now |= 1 << (3 + i)
        t = ticks_ms()
        if not self._primed:
            self._primed = True
            self._state = now  # held at start: not a press
        for i in range(len(_NAMES)):
            bit = 1 << i
            changed = self._changed_at[i]
            if (now & bit) == (self._state & bit) or (
                changed is not None and ticks_diff(t, changed) < DEBOUNCE_MS
            ):
                continue
            self._state = (self._state & ~bit) | (now & bit)
            self._changed_at[i] = t
            if self._state & bit:
                self._pressed |= bit
            else:
                self._released |= bit


def _bit(name):
    if name not in _NAMES:
        raise ValueError("unknown button {!r}".format(name))
    return 1 << _NAMES.index(name)
