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
from micropython import const

from steami.const import DEBOUNCE_MS, POLL_MS, Function, Status
from steami.handle import Handle

# The buttons, in bit order of the state. A, B and MENU are MCU pins, active low.
_NAMES = ("A", "B", "MENU", "UP", "DOWN", "LEFT", "RIGHT")
_PINS = ("A_BUTTON", "B_BUTTON", "MENU_BUTTON")
# Expander bit of UP, DOWN, LEFT and RIGHT.
_DPAD_BITS = (MCP23009_BTN_UP, MCP23009_BTN_DOWN, MCP23009_BTN_LEFT, MCP23009_BTN_RIGHT)
# After a read that found a whole D-pad tap: a button pressed again before this
# time is taken for a bounce of the press of that tap, after it for a second tap.
_BOUNCE_MS = const(5)

# The object the IRQs of A, B and MENU and the D-pad presses update: the one
# started or called last. The handlers hold no object of their own.
_active = None
# The D-pad as the expander events left it, shared by every object since it is
# the hardware: bit d for _DPAD_BITS[d] set while pressed.
_dpad_level = 0


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
        if level == MCP23009_LOGIC_LOW:
            _dpad_level |= bit
            if _active is not None:
                _active._dpad_down |= bit
        else:
            _dpad_level &= ~bit
            if _active is not None:
                _active._dpad_up |= bit

    return callback


def _attach(pin, i):
    try:
        pin.irq(_edge(i), Pin.IRQ_FALLING | Pin.IRQ_RISING, hard=True)
    except OSError:
        return  # line taken (INT_EXPANDER on EXTI 0): the button is only sampled


def _dispatch(driver):
    # Run the pad callbacks of the program held by the driver. Their errors
    # are printed and the call goes on, as for an IRQ handler: only a bus
    # error, raised outside this function, makes the D-pad read released.
    try:
        driver._dispatch_queued()
    except Exception as e:
        sys.print_exception(e)


def _setup_dpad(driver):
    # A pad event pending since before begin() is held while the arrows are
    # registered (interrupt_on_change() would dispatch it), then dispatched.
    driver._dispatching = True
    try:
        for d, bit in enumerate(_DPAD_BITS):
            driver.setup(bit, MCP23009_DIR_INPUT, MCP23009_PULLUP)
            # No event for the level at registration: it is read below.
            driver.interrupt_on_change(bit, _dpad(d))
    finally:
        driver._dispatching = False
    port = driver.get_gpio()
    _dispatch(driver)
    return port


def _read_latch(driver):
    # MCP23009E.interrupt_event() in two steps: the read, then the dispatch.
    driver._read_interrupt(0)
    _dispatch(driver)
    return True


def _wait(since, ms):
    waited = ticks_diff(ticks_ms(), since)
    if waited < ms:
        sleep_ms(ms - waited)


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
      (MCP23009E.interrupt_event()), which keeps the first change made since
      the previous read: it is taken at once. The latch does not keep the
      time of the change, so once a read changed the D-pad, the call reads it
      again 20 ms later and only the level then counts (a bounce is not a
      new tap): that call takes 20 ms more, 40 ms at most. A tap made between
      two calls then gives the same as on A, and a release is reported by
      the call that reads it. When a read found a whole tap, a press found
      20 ms later is a second tap if the button was still released 5 ms
      after the read, and a bounce of the first press otherwise.
    - The D-pad is one lever: released from one direction, it can touch the
      opposite one for a moment. A press found in the read that releases
      another direction counts only if it is still there 20 ms later.
    - was_pressed() and was_released() are flags: several presses (or
      releases) between two calls give one, and a press nobody reads is not
      reported later more than once. get_presses() counts every press.

    Limits: two D-pad taps between two reads of the expander give one (as
    does a second tap pressed within 5 ms after a read that found the first
    one whole), and a D-pad tap made while another expander interrupt is
    pending leaves no trace. Buttons uses EXTI lines 0, 7
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
        self._presses = bytearray(len(_NAMES))  # since get_presses(), up to 255
        # D-pad, bit d for _DPAD_BITS[d]: a pressed or a released level seen by
        # the expander callbacks since the last read of this object, while it
        # is active.
        self._dpad_down = 0
        self._dpad_up = 0

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
            _dpad_level = 0
            for d, bit in enumerate(_DPAD_BITS):
                if not port & (1 << bit):
                    _dpad_level |= 1 << d
        return ok

    def is_pressed(self, name):
        """True while the button is held (debounced)."""
        bit = 1 << _index(name)
        self._sample()
        return (self._state & bit) != 0

    def was_pressed(self, name):
        """True once per press, since the last time it was asked."""
        return self._take(name, 0)

    def was_released(self, name):
        """True once per release, since the last time it was asked."""
        return self._take(name, 1)

    def get_presses(self, name):
        """The presses since the last get_presses() for that button, then 0.

        As get_presses() on the micro:bit: it stops at 255 and does not depend
        on was_pressed() or wait_for_press().
        """
        i = _index(name)
        self._sample()
        presses = self._presses
        irq = disable_irq()
        n = presses[i]
        presses[i] = 0
        enable_irq(irq)
        return n

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
        bit = 1 << _index(name)
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
            return False
        self._state ^= bit
        self._changed_at[i] = t
        self._edges[0 if down else 1] |= bit
        if down and self._presses[i] < 255:
            self._presses[i] += 1
        return True

    def _edge(self, i):
        # Hard IRQ of A, B or MENU: the debounce at the time of the edge.
        if self._primed:
            self._debounce(i, self._pins[i].value() == 0, ticks_ms())

    def _read_dpad(self):
        # Reads the latch, IRQs enabled (the read uses the I2C bus): the D-pad
        # pressed now (released on an error or without the expander), the
        # pressed and the released levels seen since the last read, and True
        # when the read worked.
        ok = self._read(False, _read_latch)
        down = self._dpad_down
        up = self._dpad_up
        self._dpad_down = self._dpad_up = 0
        return (_dpad_level if ok else 0), down, up, ok

    def _settle(self, since, tapped):
        # Once a read changed the D-pad, the latch is read again 20 ms later:
        # what changed in between is a bounce, and only the level then
        # counts. A change that level gives is settled the same way, once.
        # tapped: the buttons the read found as a whole tap. A read 5 ms after
        # it tells a second tap (still released then) from a bounce.
        lifted = 0
        if tapped:
            _wait(since, _BOUNCE_MS)
            lifted = tapped & ~self._read_dpad()[0]
        for _ in range(2):
            _wait(since, DEBOUNCE_MS)
            level = self._read_dpad()[0]
            irq = disable_irq()
            t = ticks_ms()
            changed = False
            for d in range(4):
                i = 3 + d
                bit = 1 << i
                held = (level >> d) & 1 == 1
                if held and (lifted >> d) & 1 and self._state & bit:
                    # The release of the first tap, then the press of a
                    # second one: the button stays pressed.
                    self._edges[0] |= bit
                    self._edges[1] |= bit
                    if self._presses[i] < 255:
                        self._presses[i] += 1
                    self._changed_at[i] = t
                    changed = True
                elif self._debounce(i, held, t):
                    changed = True
            enable_irq(irq)
            lifted = 0
            if not changed:
                return
            since = t

    def _sample(self):
        global _active
        if self._status == Status.NOT_STARTED:
            self.begin()
        _active = self
        # The D-pad first, IRQs enabled: the read uses the I2C bus.
        dpad, down, up, ok = self._read_dpad()

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
        # D-pad: the first change the latch kept, at once; the level after it
        # is for _settle(). Releases first: a press found as the lever leaves
        # another direction is a rebound unless _settle() finds it again.
        settle = released = False
        tapped = 0  # pressed then released, both found by this read
        for d in range(4):
            bit = 1 << d
            if (
                self._state & (8 << d)
                and (up & bit or not dpad & bit)
                and self._debounce(3 + d, False, t)
            ):
                settle = released = True
        for d in range(4):
            bit = 1 << d
            if self._state & (8 << d) or not (down | dpad) & bit:
                continue
            if released and dpad & bit:
                settle = True
            elif self._debounce(3 + d, True, t):
                settle = True
                if not dpad & bit:
                    tapped |= bit
        enable_irq(irq)
        if ok and settle:
            self._settle(t, tapped)


def _index(name):
    if name not in _NAMES:
        raise ValueError("unknown button {!r}".format(name))
    return _NAMES.index(name)
