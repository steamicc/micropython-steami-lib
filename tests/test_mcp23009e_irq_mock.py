"""Mock tests of the mcp23009e interrupt path (issue #465).

A small register model of the MCP23009 stands for the chip on the I2C bus.
It keeps the interrupt logic that matters here: the first change on an
enabled pin sets INTF and copies the port into INTCAP, later changes are
ignored until the interrupt is cleared, and reading GPIO (or INTCAP when
IOCON.INTCC is set) clears it.

The tests call interrupt_event() where the scheduled soft IRQ would run on
the board, so they can delay it after a press, as a long blocking call
does on a V1c.
"""

import importlib

import pytest

from tests.fake_machine import FakePin
from tests.runner.executor import cleanup_driver, load_driver_mock

ADDR = 0x20

IODIR = 0x00
IPOL = 0x01
GPINTEN = 0x02
DEFVAL = 0x03
INTCON = 0x04
IOCON = 0x05
GPPU = 0x06
INTF = 0x07
INTCAP = 0x08
GPIO = 0x09
OLAT = 0x0A

# D-pad of the STeaMi V1c: active low, with pull-ups.
UP = 7
DOWN = 5
LEFT = 6
RIGHT = 4
DPAD = (UP, DOWN, LEFT, RIGHT)
RELEASED = 0xF0


class FakeMCP23009:
    """Register model of the MCP23009 interrupt logic, seen as an I2C bus.

    In "previous state" mode (INTCON bit clear), a pin is compared with a
    reference: the port value at the last read that cleared the interrupt.
    With this model, enabling a pin that changed since the last clear
    raises an interrupt at once: the spurious event seen on a V1c, when
    the reference is still the port before the pull-ups were set (0x00).

    Args:
        pins: input levels of the port.
        reference: port value at the last clear (default: pins).
    """

    def __init__(self, pins=RELEASED, reference=None):
        self.regs = [0] * 11
        self.regs[IODIR] = 0xFF
        self.pins = pins
        self.reference = pins if reference is None else reference
        self.log = []
        # Called as on_write(reg, value) once a write is applied, to run
        # code where a scheduled IRQ could run on the board.
        self.on_write = None

    # ----- Chip side -----

    def press(self, gp):
        self.pins &= ~(1 << gp)
        self._update()

    def release(self, gp):
        self.pins |= 1 << gp
        self._update()

    def latch(self, gp):
        """Leave a pending interrupt on gp, as a change before registration."""
        self.regs[INTF] = 1 << gp
        self.regs[INTCAP] = self.pins

    def _update(self):
        if self.regs[INTF]:
            return
        intcon = self.regs[INTCON]
        changed = ((self.pins ^ self.reference) & ~intcon) | (
            (self.pins ^ self.regs[DEFVAL]) & intcon
        )
        changed &= self.regs[GPINTEN]
        if changed:
            self.regs[INTF] = changed
            self.regs[INTCAP] = self.pins

    def _clear(self):
        self.regs[INTF] = 0
        self.reference = self.pins
        self._update()

    # ----- I2C side -----

    def readfrom_mem(self, addr, reg, nbytes, *, addrsize=8):
        assert addr == ADDR
        self.log.append(("r", reg))
        value = self.pins if reg == GPIO else self.regs[reg]
        clearing = INTCAP if self.regs[IOCON] & 0x01 else GPIO
        if reg == clearing:
            self._clear()
        return bytes([value])

    def writeto_mem(self, addr, reg, buf, *, addrsize=8):
        assert addr == ADDR
        self.log.append(("w", reg))
        self.regs[reg] = buf[0]
        self._update()
        if self.on_write is not None:
            self.on_write(reg, buf[0])


@pytest.fixture
def drv(monkeypatch):
    module, _ = load_driver_mock("mcp23009e", None)
    monkeypatch.setattr(module, "sleep_ms", lambda ms: None)
    module.pin = importlib.import_module("mcp23009e.pin")
    module.active_low_pin = importlib.import_module("mcp23009e.active_low_pin")
    yield module
    cleanup_driver("mcp23009e")


@pytest.fixture
def chip():
    return FakeMCP23009()


@pytest.fixture
def dev(drv, chip):
    return drv.MCP23009E(chip, ADDR, reset_pin=FakePin(0))


def dpad_pin(drv, dev, gp):
    pin_cls = drv.pin.MCP23009Pin
    return pin_cls(dev, gp, pin_cls.IN, pin_cls.PULL_UP)


def recorder(events, name):
    """Handler that logs the captured and the current level of its pin."""

    def handler(pin):
        events.append((name, pin.irq_level(), pin.value()))

    return handler


BOTH = 1 | 2  # IRQ_FALLING | IRQ_RISING


# ----- Captured level -----


def test_irq_level_is_none_before_any_interrupt(drv, dev):
    btn = dpad_pin(drv, dev, UP)
    assert btn.irq_level() is None


def test_handler_sees_press_released_before_it_runs(drv, dev, chip):
    events = []
    btn = dpad_pin(drv, dev, UP)
    btn.irq(recorder(events, "UP"), BOTH)
    chip.press(UP)
    chip.release(UP)  # released before the soft IRQ runs
    dev.interrupt_event()
    # Captured level: pressed. Current level: released.
    assert events == [("UP", 0, 1)]


def test_press_then_release_each_reported(drv, dev, chip):
    events = []
    btn = dpad_pin(drv, dev, UP)
    btn.irq(recorder(events, "UP"), BOTH)
    chip.press(UP)
    dev.interrupt_event()
    chip.release(UP)
    dev.interrupt_event()
    assert events == [("UP", 0, 0), ("UP", 1, 1)]


def test_value_in_handler_reads_current_gpio(drv, dev, chip):
    events = []
    btn = dpad_pin(drv, dev, LEFT)
    btn.irq(recorder(events, "LEFT"), BOTH)
    chip.press(LEFT)
    dev.interrupt_event()
    assert events == [("LEFT", 0, 0)]
    # value() reads GPIO again once the handler has run.
    chip.release(LEFT)
    assert btn.value() == 1
    assert btn.irq_level() == 0


def test_change_callback_gets_level_from_intcap(drv, dev, chip):
    levels = []
    dpad_pin(drv, dev, RIGHT)
    dev.interrupt_on_change(RIGHT, levels.append)
    chip.press(RIGHT)
    chip.release(RIGHT)
    dev.interrupt_event()
    assert levels == [0]


def test_intcc_set_reads_intcap_only(drv, dev, chip):
    dev.set_iocon(0x01)  # INTCC: reading INTCAP clears the interrupt
    events = []
    btn = dpad_pin(drv, dev, UP)
    btn.irq(recorder(events, "UP"), BOTH)
    chip.press(UP)
    chip.release(UP)
    chip.log.clear()
    dev.interrupt_event()
    assert ("r", INTCAP) in chip.log[:4]
    service_reads = chip.log[: chip.log.index(("r", INTCAP)) + 1]
    assert ("r", GPIO) not in service_reads
    assert events == [("UP", 0, 1)]
    assert chip.regs[INTF] == 0


def test_active_low_pin_inverts_captured_level(drv, dev, chip):
    pin_cls = drv.active_low_pin.MCP23009ActiveLowPin
    btn = pin_cls(dev, UP, pin_cls.IN, pin_cls.PULL_UP)
    assert btn.irq_level() is None
    events = []
    btn.irq(recorder(events, "UP"), BOTH)
    chip.press(UP)
    chip.release(UP)
    dev.interrupt_event()
    # Logical level: pressed is 1 on an active-low pin.
    assert events == [("UP", 1, 0)]


# ----- Edge filters -----


def test_falling_only_handler(drv, dev, chip):
    events = []
    btn = dpad_pin(drv, dev, DOWN)
    btn.irq(recorder(events, "DOWN"), btn.IRQ_FALLING)
    chip.press(DOWN)
    dev.interrupt_event()
    chip.release(DOWN)
    dev.interrupt_event()
    assert events == [("DOWN", 0, 0)]


def test_falling_only_handler_with_late_soft_irq(drv, dev, chip):
    events = []
    btn = dpad_pin(drv, dev, DOWN)
    btn.irq(recorder(events, "DOWN"), btn.IRQ_FALLING)
    chip.press(DOWN)
    chip.release(DOWN)
    dev.interrupt_event()
    assert events == [("DOWN", 0, 1)]


def test_rising_only_handler(drv, dev, chip):
    events = []
    btn = dpad_pin(drv, dev, DOWN)
    btn.irq(recorder(events, "DOWN"), btn.IRQ_RISING)
    chip.press(DOWN)
    dev.interrupt_event()
    assert events == []
    chip.release(DOWN)
    dev.interrupt_event()
    assert events == [("DOWN", 1, 1)]


def test_device_falling_and_rising_callbacks(drv, dev, chip):
    calls = []
    dpad_pin(drv, dev, LEFT)
    dpad_pin(drv, dev, RIGHT)
    dev.interrupt_on_falling(LEFT, lambda: calls.append("fall"))
    dev.interrupt_on_raising(RIGHT, lambda: calls.append("rise"))
    chip.press(LEFT)
    dev.interrupt_event()
    chip.press(RIGHT)
    dev.interrupt_event()
    chip.release(LEFT)
    dev.interrupt_event()
    chip.release(RIGHT)
    dev.interrupt_event()
    assert calls == ["fall", "rise"]


def test_disable_interrupt_stops_callbacks(drv, dev, chip):
    events = []
    btn = dpad_pin(drv, dev, UP)
    btn.irq(recorder(events, "UP"), BOTH)
    dev.disable_interrupt(UP)
    chip.press(UP)
    dev.interrupt_event()
    assert events == []
