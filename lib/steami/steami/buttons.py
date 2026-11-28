import sys
from time import sleep_ms, ticks_diff, ticks_ms

from machine import Pin, disable_irq, enable_irq
from mcp23009e.const import (
    MCP23009_BTN_DOWN,
    MCP23009_BTN_LEFT,
    MCP23009_BTN_RIGHT,
    MCP23009_BTN_UP,
    MCP23009_DIR_INPUT,
    MCP23009_LOGIC_LOW,
    MCP23009_PULLUP,
)

from steami.const import DEBOUNCE_MS, POLL_MS, Function, Status
from steami.handle import Handle

# The buttons, in bit order of the state. A, B and MENU are MCU pins, active low.
_NAMES = ("A", "B", "MENU", "UP", "DOWN", "LEFT", "RIGHT")
_PINS = ("A_BUTTON", "B_BUTTON", "MENU_BUTTON")
# Expander bit of UP, DOWN, LEFT and RIGHT.
_DPAD_BITS = (MCP23009_BTN_UP, MCP23009_BTN_DOWN, MCP23009_BTN_LEFT, MCP23009_BTN_RIGHT)

# The object the IRQs of A, B and MENU and the D-pad presses update: the one
# started or called last. The handlers hold no object of their own.
_active = None
# The D-pad as the expander events left it, shared by every object since it is
# the hardware: bit d for _DPAD_BITS[d] set while pressed, and the time of the
# last event of each button.
_dpad_level = 0
_dpad_event_at = [0] * 4


def _locked(t, stamp):
    # Within 20 ms after stamp. A stamp older than half the ticks period reads
    # as negative (ticks wrap): it no longer locks.
    return 0 <= ticks_diff(t, stamp) < DEBOUNCE_MS


def _edge(i):
    # Hard IRQ of A, B or MENU: no allocation, no I2C.
    def handler(pin):
        if _active is not None:
            _active._edge(i)

    return handler


def _dpad(d):
    # Run by MCP23009E.interrupt_event(), once per event, in order: the level
    # captured at the interrupt, then the current one.
    bit = 1 << d

    def callback(level):
        global _dpad_level
        _dpad_event_at[d] = ticks_ms()
        if level == MCP23009_LOGIC_LOW:
            _dpad_level |= bit
            if _active is not None:
                _active._dpad_down |= bit
        else:
            _dpad_level &= ~bit

    return callback


def _attach(pin, i):
    try:
        pin.irq(_edge(i), Pin.IRQ_FALLING | Pin.IRQ_RISING, hard=True)
    except OSError:
        return  # line taken (INT_EXPANDER on EXTI 0): the button is only sampled


def _setup_dpad(driver):
    for d, bit in enumerate(_DPAD_BITS):
        driver.setup(bit, MCP23009_DIR_INPUT, MCP23009_PULLUP)
        # No event for the level at registration: it is read below.
        driver.interrupt_on_change(bit, _dpad(d))
    return driver.get_gpio()


def _read_latch(driver):
    # MCP23009E.interrupt_event() in two steps. A bus error in the read makes
    # the D-pad read released. An error of a pad callback of the program, run
    # by the dispatch, is printed and the call goes on, as for an IRQ handler.
    driver._read_interrupt(0)
    try:
        driver._dispatch_queued()
    except Exception as e:
        sys.print_exception(e)
    return True


class Buttons(Handle):
    """The A, B and MENU buttons and the D-pad (UP, DOWN, LEFT, RIGHT).

    Buttons are named by text: "A", "B", "MENU", "UP", "DOWN", "LEFT", "RIGHT";
    any other name raises ValueError. A, B and MENU are MCU pins and always
    work. The D-pad is on the MCP23009E: when it does not answer, the D-pad
    reads as released. Creating it touches no hardware.

    Every call samples the buttons. Debounce is 20 ms: a change is taken at
    once, then the bounces of the next 20 ms are ignored. A tap made between
    two calls is not missed, whatever the time between them:

    - A, B and MENU: begin() sets a hard IRQ on both edges of each pin, which
      runs the debounce at the time of the edge. A tap made between two calls
      gives, at the next call, was_pressed() and was_released() true and
      is_pressed() false.
    - D-pad: no MCU interrupt (INT_EXPANDER, PB0, shares EXTI line 0 with
      MENU, PA0). Each call reads the latch of the expander
      (MCP23009E.interrupt_event()). A press found there is taken if 20 ms
      passed since the last accepted change; a release only once the reads
      found no change on that button for 20 ms. A tap made between two calls
      gives was_pressed() and is_pressed() true at the next call; the release
      comes at the first call made 20 ms or more after it.
    - At most one press per button between two calls (a flag, not a counter).

    Limits: a D-pad tap made before the release of the previous one is
    reported merges with it; a D-pad press and its release made while another
    expander interrupt is pending leave no trace. Buttons uses EXTI lines 0, 7
    and 8: a line already taken (MCP23009E(interrupt_pin=Pin("INT_EXPANDER"))
    takes line 0) leaves that button sampled at each call only, and a later
    Pin.irq() on such a line raises OSError. With several Buttons objects, the
    taps made between two calls go to the one started or called last only;
    every object follows the levels of all the buttons. A pad callback set
    with Steami.mcp23009e().interrupt_on_*() runs during the calls; an error
    it raises is printed and does not stop the call.
    """

    _NOUN = "D-PAD expander"
    _HINT = "The A, B and MENU buttons still work."
    _FALLBACK = "the D-PAD will read as released."

    def __init__(self):
        super().__init__(Function.BUTTONS)
        self._pins = None
        self._primed = False
        # Shared with the IRQs: changed with the interrupts disabled.
        self._state = 0  # bit i set: button i pressed
        self._edges = [0, 0]  # latched presses, latched releases
        self._changed_at = [0] * len(_NAMES)  # time of the last accepted change
        # D-pad, bit d for _DPAD_BITS[d]: a press seen by the expander
        # callbacks since the last sample of this object, while it is active.
        self._dpad_down = 0

    def begin(self):
        """Set the pins and their IRQs up and find the D-pad expander.

        True when it answered. A, B and MENU work whatever the answer.
        """
        global _active, _dpad_level
        if self._pins is None:
            self._pins = [Pin(name, Pin.IN, Pin.PULL_UP) for name in _PINS]
            _active = self
            for i, pin in enumerate(self._pins):
                _attach(pin, i)
        if self._status != Status.NOT_STARTED:
            return super().begin()
        ok = super().begin()
        if ok:
            port = self._read(None, _setup_dpad)
            if port is None:
                port = 0xFF  # on an error the D-pad reads released
            t = ticks_ms() - DEBOUNCE_MS
            _dpad_level = 0
            for d, bit in enumerate(_DPAD_BITS):
                if not port & (1 << bit):
                    _dpad_level |= 1 << d
                _dpad_event_at[d] = t
        return ok

    def is_pressed(self, name):
        """True while the button is held (debounced)."""
        bit = _bit(name)
        self._sample()
        return (self._state & bit) != 0

    def was_pressed(self, name):
        """True once per press, since the last time it was asked."""
        return self._take(name, 0)

    def was_released(self, name):
        """True once per release, since the last time it was asked."""
        return self._take(name, 1)

    def wait_for_press(self, timeout_ms=None):
        """Wait for a new press and return the name of the button.

        Returns None after timeout_ms; with None, waits forever. Presses made
        before the call are dropped, the taps latched by an IRQ or by the
        expander included, and a button already held must be released first.
        """
        self._sample()  # takes what happened before the call
        edges = self._edges
        irq = disable_irq()
        edges[0] = 0
        enable_irq(irq)
        start = ticks_ms()
        while True:
            self._sample()
            irq = disable_irq()
            pressed = edges[0]
            first = pressed & -pressed  # the lowest bit is taken
            edges[0] = pressed & ~first
            enable_irq(irq)
            for i, name in enumerate(_NAMES):
                if first >> i == 1:
                    return name
            if timeout_ms is not None and ticks_diff(ticks_ms(), start) >= timeout_ms:
                return None
            sleep_ms(POLL_MS)

    def _take(self, name, k):
        bit = _bit(name)
        self._sample()
        edges = self._edges
        irq = disable_irq()
        found = edges[k] & bit
        edges[k] &= ~bit
        enable_irq(irq)
        return found != 0

    def _debounce(self, i, down, t):
        # Lock-out debounce of button i with its level `down` at time t. Runs
        # from the IRQ of the pin and from _sample() with the IRQs disabled.
        bit = 1 << i
        if down == ((self._state & bit) != 0) or _locked(t, self._changed_at[i]):
            return
        self._state ^= bit
        self._changed_at[i] = t
        self._edges[0 if down else 1] |= bit

    def _edge(self, i):
        # Hard IRQ of A, B or MENU: the debounce at the time of the edge.
        if self._primed:
            self._debounce(i, self._pins[i].value() == 0, ticks_ms())

    def _sample(self):
        global _active
        if self._status == Status.NOT_STARTED:
            self.begin()
        _active = self
        # The D-pad first, IRQs enabled: the read uses the I2C bus. On an
        # error the D-pad reads released, with no event.
        dpad = _dpad_level if self._read(False, _read_latch) else 0
        down = self._dpad_down
        self._dpad_down = 0

        irq = disable_irq()
        t = ticks_ms()
        mcu = 0
        for i in range(3):
            if self._pins[i].value() == 0:
                mcu |= 1 << i
        if not self._primed:
            self._primed = True
            self._state = mcu | (dpad << 3)  # held at start: not a press
            for i in range(len(_NAMES)):
                self._changed_at[i] = t - DEBOUNCE_MS  # the next change is taken at once
            enable_irq(irq)
            return
        # A, B and MENU: the IRQ took the edges; the level read here catches
        # what it could not (a change at the end of a lock-out, a line taken).
        for i in range(3):
            self._debounce(i, (mcu & (1 << i)) != 0, t)
        # D-pad: a press found in the latch or in the level; a release only
        # after 20 ms without an event on that button.
        for d in range(4):
            i = 3 + d
            bit = 1 << d
            if not self._state & (1 << i):
                if (down | dpad) & bit:
                    self._debounce(i, True, t)
            elif not dpad & bit and not _locked(t, _dpad_event_at[d]):
                self._debounce(i, False, t)
        enable_irq(irq)


def _bit(name):
    if name not in _NAMES:
        raise ValueError("unknown button {!r}".format(name))
    return 1 << _NAMES.index(name)
