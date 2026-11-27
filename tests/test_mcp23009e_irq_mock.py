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
        # Called as on_write(reg, value) once a write is applied, and as
        # on_read(reg) once a read is applied, to run code where a
        # scheduled IRQ could run on the board.
        self.on_write = None
        self.on_read = None

    # ----- Chip side -----

    def press(self, gp):
        self.pins &= ~(1 << gp)
        self._update()

    def release(self, gp):
        self.pins |= 1 << gp
        self._update()

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
        if self.on_read is not None:
            self.on_read(reg)
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


def test_intcc_set_clears_on_intcap_read(drv, dev, chip):
    dev.set_iocon(0x01)  # INTCC: reading INTCAP clears the interrupt
    events = []
    btn = dpad_pin(drv, dev, UP)
    btn.irq(recorder(events, "UP"), BOTH)
    chip.press(UP)
    chip.release(UP)
    chip.log.clear()
    dev.interrupt_event()
    assert chip.log[:3] == [("r", INTF), ("r", INTCAP), ("r", GPIO)]
    assert events == [("UP", 0, 1)]
    assert chip.regs[INTF] == 0
    dev.interrupt_event()
    assert events == [("UP", 0, 1)]


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


# ----- Registration -----


def test_registering_dpad_handlers_fires_no_event(drv, dev, chip):
    events = []
    pins = [dpad_pin(drv, dev, gp) for gp in DPAD]
    chip.reference = 0x00  # port value before the pull-ups were set
    for gp, pin in zip(DPAD, pins):
        pin.irq(recorder(events, gp), BOTH)
    dev.interrupt_event()  # the soft IRQ, if INT was raised
    assert events == []
    assert chip.regs[INTF] == 0


def _reregister_with_pending_press(drv, dev, chip):
    first = []
    second = []
    btn = dpad_pin(drv, dev, UP)
    btn.irq(recorder(first, "first"), BOTH)
    chip.press(UP)  # the soft IRQ has not run yet
    assert chip.regs[INTF] == 1 << UP
    btn.irq(recorder(second, "second"), BOTH)
    assert chip.regs[INTF] == 0
    dev.interrupt_event()
    assert first == []
    assert second == []


def test_reregistration_clears_pending_interrupt(drv, dev, chip):
    _reregister_with_pending_press(drv, dev, chip)


def test_reregistration_clears_pending_interrupt_with_intcc(drv, dev, chip):
    dev.set_iocon(0x01)
    _reregister_with_pending_press(drv, dev, chip)


def test_callback_stored_and_interrupt_cleared_before_gpinten(drv, dev, chip):
    """A soft IRQ that runs as GPINTEN is written finds the new callback
    and no stale interrupt."""
    events = []
    seen = []
    btn = dpad_pin(drv, dev, UP)
    chip.reference = 0x00  # a change latched before registration

    def on_write(reg, value):
        if reg == GPINTEN and value & (1 << UP):
            seen.append((dev.events_change[UP] is not None, chip.regs[INTF]))
            dev.interrupt_event()

    chip.on_write = on_write
    btn.irq(recorder(events, "UP"), BOTH)
    assert seen == [(True, 0)]
    assert events == []


def test_press_at_enable_time_reaches_new_handler(drv, dev, chip):
    events = []
    btn = dpad_pin(drv, dev, UP)

    def on_write(reg, value):
        if reg == GPINTEN and value & (1 << UP):
            chip.press(UP)
            dev.interrupt_event()

    chip.on_write = on_write
    btn.irq(recorder(events, "UP"), BOTH)
    assert events == [("UP", 0, 0)]


def test_intcon_written_before_gpinten(drv, dev, chip):
    dpad_pin(drv, dev, UP)
    chip.log.clear()
    dev.interrupt_on_change(UP, lambda level: None)
    writes = [reg for op, reg in chip.log if op == "w"]
    assert writes.index(INTCON) < writes.index(GPINTEN)


def test_pending_event_on_other_pin_is_kept(drv, dev, chip):
    events = []
    down = dpad_pin(drv, dev, DOWN)
    up = dpad_pin(drv, dev, UP)
    down.irq(recorder(events, "DOWN"), BOTH)
    chip.press(DOWN)  # the soft IRQ has not run yet
    up.irq(recorder(events, "UP"), BOTH)
    dev.interrupt_event()
    assert events == [("DOWN", 0, 0)]


def test_handler_run_at_registration_can_enable_another_pin(drv, dev, chip):
    """A handler called during a registration enables DOWN: the
    registration must not write back an older GPINTEN without DOWN."""
    events = []
    left = dpad_pin(drv, dev, LEFT)
    down = dpad_pin(drv, dev, DOWN)
    right = dpad_pin(drv, dev, RIGHT)

    def on_left(pin):
        events.append(("LEFT", pin.irq_level()))
        down.irq(recorder(events, "DOWN"), BOTH)

    left.irq(on_left, BOTH)
    chip.press(LEFT)  # pending when RIGHT is registered
    right.irq(recorder(events, "RIGHT"), BOTH)
    assert events == [("LEFT", 0)]
    assert chip.regs[GPINTEN] == (1 << LEFT) | (1 << DOWN) | (1 << RIGHT)
    chip.press(DOWN)
    dev.interrupt_event()
    assert events == [("LEFT", 0), ("DOWN", 0, 0)]


def test_handler_run_at_registration_can_disable_its_pin(drv, dev, chip):
    """A one-shot handler, called during a registration, disables its own
    pin: the registration must not enable it again."""
    events = []
    left = dpad_pin(drv, dev, LEFT)
    right = dpad_pin(drv, dev, RIGHT)

    def once(pin):
        events.append("LEFT")
        dev.disable_interrupt(LEFT)

    left.irq(once, BOTH)
    chip.press(LEFT)
    right.irq(recorder(events, "RIGHT"), BOTH)
    assert events == ["LEFT"]
    assert chip.regs[GPINTEN] == 1 << RIGHT


def test_soft_irq_after_registration_read_reports_event_once(drv, dev, chip):
    """The soft IRQ of a DOWN press runs at the first scheduler point after
    the interrupt is read during the registration of UP: one DOWN event."""
    events = []
    down = dpad_pin(drv, dev, DOWN)
    up = dpad_pin(drv, dev, UP)
    down.irq(recorder(events, "DOWN"), BOTH)
    chip.press(DOWN)
    ran = []

    def on_read(reg):
        if reg == GPIO and not ran:
            ran.append(reg)
            dev.interrupt_event()

    chip.on_read = on_read
    up.irq(recorder(events, "UP"), BOTH)
    assert ran == [GPIO]
    assert events == [("DOWN", 0, 0)]


def test_interrupt_read_and_clear_have_no_scheduler_point():
    """MicroPython runs scheduled soft IRQs at jumps (if, loops, and, or).
    None may sit between the INTF read and the read that clears the
    interrupt, or a soft IRQ could report the same event a second time."""
    import ast
    from pathlib import Path

    path = Path(__file__).parents[1] / "lib/mcp23009e/mcp23009e/device.py"
    tree = ast.parse(path.read_text())
    func = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_service_interrupt"
    )

    def reads(node, name):
        return any(isinstance(sub, ast.Name) and sub.id == name for sub in ast.walk(node))

    body = func.body
    start = next(i for i, st in enumerate(body) if reads(st, "MCP23009_INTF"))
    end = next(i for i, st in enumerate(body) if reads(st, "MCP23009_GPIO"))
    assert start < end
    for statement in body[start : end + 1]:
        assert isinstance(statement, (ast.Assign, ast.Expr))
        for sub in ast.walk(statement):
            assert not isinstance(sub, (ast.If, ast.IfExp, ast.BoolOp, ast.For, ast.While))


def test_disable_interrupt_stops_callbacks(drv, dev, chip):
    events = []
    btn = dpad_pin(drv, dev, UP)
    btn.irq(recorder(events, "UP"), BOTH)
    dev.disable_interrupt(UP)
    chip.press(UP)
    dev.interrupt_event()
    assert events == []
