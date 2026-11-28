"""Mock tests of the mcp23009e interrupt path (issue #465).

A small register model of the MCP23009 (tests/fake_machine/mcp23009.py)
stands for the chip on the I2C bus.

The tests call interrupt_event() where the scheduled soft IRQ would run on
the board, so they can delay it after a press, as a long blocking call
does on a V1c.
"""

import ast
import importlib
from itertools import pairwise
from pathlib import Path

import pytest

from tests.fake_machine import FakePin
from tests.fake_machine.mcp23009 import (
    ADDR,
    DOWN,
    DPAD,
    GPINTEN,
    GPIO,
    INTCAP,
    INTCON,
    INTF,
    LEFT,
    RELEASED,
    RIGHT,
    UP,
    FakeMCP23009,
)
from tests.runner.executor import cleanup_driver, load_driver_mock


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
    # The press, with the captured level, then the release read from GPIO.
    assert events == [("UP", 0, 1), ("UP", 1, 1)]


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
    assert levels == [0, 1]


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
    assert events == [("UP", 0, 1), ("UP", 1, 1)]
    # Datasheet 1.7.4, note: the release made while INTF was set is still
    # there when the read clears it, so the interrupt sets again.
    assert chip.regs[INTF] == 1 << UP
    dev.interrupt_event()
    assert chip.regs[INTF] == 0
    assert events == [("UP", 0, 1), ("UP", 1, 1)]


def test_interrupt_set_again_after_a_tap_gives_no_second_event(drv, dev, chip):
    # The release made while INTF was set is still pending once the read
    # clears the interrupt, which sets again with a new INTCAP. The next read
    # finds the level it already reported: no second event.
    levels = []
    dpad_pin(drv, dev, UP)
    dev.interrupt_on_change(UP, levels.append)
    chip.press(UP)
    chip.release(UP)
    dev.interrupt_event()
    assert chip.regs[INTF] == 1 << UP
    assert chip.regs[INTCAP] == RELEASED
    dev.interrupt_event()
    assert chip.regs[INTF] == 0
    assert levels == [0, 1]


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
    assert events == [("UP", 1, 0), ("UP", 0, 0)]


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
    dev.interrupt_on_rising(RIGHT, lambda: calls.append("rise"))
    chip.press(LEFT)
    dev.interrupt_event()
    chip.press(RIGHT)
    dev.interrupt_event()
    chip.release(LEFT)
    dev.interrupt_event()
    chip.release(RIGHT)
    dev.interrupt_event()
    assert calls == ["fall", "rise"]


def test_interrupt_on_raising_is_a_deprecated_alias(drv, dev, chip):
    # Old spelling kept for the whole 1.x series (arduino-steami-lib#183).
    assert drv.MCP23009E.interrupt_on_raising is drv.MCP23009E.interrupt_on_rising
    calls = []
    dpad_pin(drv, dev, RIGHT)
    dev.interrupt_on_raising(RIGHT, lambda: calls.append("rise"))
    chip.press(RIGHT)
    dev.interrupt_event()
    chip.release(RIGHT)
    dev.interrupt_event()
    assert calls == ["rise"]


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
    the interrupt is read during the registration of UP (just after the
    GPINTEN write, which follows the read with no jump): one DOWN event."""
    events = []
    down = dpad_pin(drv, dev, DOWN)
    up = dpad_pin(drv, dev, UP)
    down.irq(recorder(events, "DOWN"), BOTH)
    chip.press(DOWN)
    ran = []

    def on_write(reg, value):
        if reg == GPINTEN and value & (1 << UP) and not ran:
            ran.append(reg)
            dev.interrupt_event()

    chip.on_write = on_write
    up.irq(recorder(events, "UP"), BOTH)
    assert ran == [GPINTEN]
    assert events == [("DOWN", 0, 0)]


# Statements and expressions that compile to a jump in MicroPython.
JUMPS = (ast.If, ast.IfExp, ast.BoolOp, ast.For, ast.While, ast.Try)


def _device_function(name):
    path = Path(__file__).parents[1] / "lib/mcp23009e/mcp23009e/device.py"
    tree = ast.parse(path.read_text())
    return next(
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name
    )


def test_interrupt_read_and_queueing_have_no_scheduler_point():
    """MicroPython runs scheduled soft IRQs at jumps (if, loops, and, or).
    None may sit between the INTF read, the read that clears the interrupt,
    the update of the last known levels and the queueing of the events, or
    a soft IRQ could report the same event a second time, compare with
    stale levels, or queue its later events first."""
    func = _device_function("_read_interrupt")
    calls = [
        sub
        for sub in ast.walk(func)
        if isinstance(sub, ast.Call)
        and isinstance(sub.func, ast.Attribute)
        and sub.func.attr == "_read_reg"
    ]
    assert len(calls) == 3
    for sub in ast.walk(func):
        assert not isinstance(sub, JUMPS)


def test_registration_has_no_scheduler_point_before_dispatch():
    """From the INTCON write to the GPINTEN write, the registration has no
    jump: a soft IRQ runs only once gpx is enabled, its level is read and
    the pending events are queued."""
    func = _device_function("_send_enable_interrupt")
    for sub in ast.walk(func):
        assert not isinstance(sub, JUMPS)
    last = func.body[-1]
    assert isinstance(last, ast.Expr)
    assert last.value.func.attr == "_dispatch_queued"


@pytest.mark.parametrize("name", ("_send_enable_interrupt", "_send_disable_interrupt"))
def test_register_read_modify_writes_have_no_scheduler_point(name):
    """Each read-modify-write of GPINTEN, INTCON or DEFVAL is one statement
    with no jump: a soft IRQ run between the read and the write could change
    the register and have its change overwritten."""
    func = _device_function(name)
    writes = [
        node
        for node in ast.walk(func)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_write_reg"
    ]
    assert len(writes) >= 1
    for call in writes:
        # The read is inside the write call itself.
        assert any(
            isinstance(sub, ast.Attribute) and sub.attr == "_read_reg" for sub in ast.walk(call)
        )
        for sub in ast.walk(call):
            assert not isinstance(sub, JUMPS)
            assert not (isinstance(sub, ast.Name) and sub.id == "_set_bit")


def test_disable_interrupt_stops_callbacks(drv, dev, chip):
    events = []
    btn = dpad_pin(drv, dev, UP)
    btn.irq(recorder(events, "UP"), BOTH)
    dev.disable_interrupt(UP)
    chip.press(UP)
    dev.interrupt_event()
    assert events == []


# ----- Changes the chip misses while an interrupt is pending -----


def register_dpad(drv, dev, events):
    pins = {}
    for name, gp in (("UP", UP), ("DOWN", DOWN), ("LEFT", LEFT), ("RIGHT", RIGHT)):
        pins[name] = dpad_pin(drv, dev, gp)
        pins[name].irq(recorder(events, name), BOTH)
    return pins


def test_v1c_lost_release_during_pending_press(drv, dev, chip):
    """V1c measurement (a): LEFT pressed, then UP pressed; LEFT released
    while the UP interrupt is pending. The chip never signals the LEFT
    release: the driver reports it from GPIO, after the UP press."""
    events = []
    register_dpad(drv, dev, events)
    chip.press(LEFT)
    dev.interrupt_event()
    chip.press(UP)
    chip.release(LEFT)  # INTF is set (UP): no interrupt for LEFT
    dev.interrupt_event()
    chip.release(UP)
    dev.interrupt_event()
    chip.press(LEFT)
    dev.interrupt_event()
    assert events == [
        ("LEFT", 0, 0),
        ("UP", 0, 0),
        ("LEFT", 1, 1),
        ("UP", 1, 1),
        ("LEFT", 0, 0),
    ]


def test_v1c_lost_press_during_pending_press(drv, dev, chip):
    """V1c measurement (b): RIGHT released, UP pressed, RIGHT pressed while
    the UP interrupt is pending, then RIGHT released. Without the GPIO
    comparison, the release came with no press before it."""
    events = []
    register_dpad(drv, dev, events)
    chip.press(RIGHT)
    dev.interrupt_event()
    chip.release(RIGHT)
    dev.interrupt_event()
    chip.press(UP)
    chip.press(RIGHT)  # INTF is set (UP): no interrupt for RIGHT
    dev.interrupt_event()
    chip.release(RIGHT)
    dev.interrupt_event()
    chip.release(UP)
    dev.interrupt_event()
    assert events == [
        ("RIGHT", 0, 0),
        ("RIGHT", 1, 1),
        ("UP", 0, 0),
        ("RIGHT", 0, 0),
        ("RIGHT", 1, 1),
        ("UP", 1, 1),
    ]


def test_short_tap_gives_press_then_release(drv, dev, chip):
    levels = []
    btn = dpad_pin(drv, dev, DOWN)

    def handler(pin):
        levels.append(pin.irq_level())

    btn.irq(handler, BOTH)
    chip.press(DOWN)
    chip.release(DOWN)
    dev.interrupt_event()
    assert levels == [0, 1]
    dev.interrupt_event()
    assert levels == [0, 1]


def test_captured_level_equal_to_last_known_is_not_reported_twice(drv, dev, chip):
    """With IOCON.INTCC, reading INTCAP clears the interrupt: a press just
    after it raises a new interrupt and is also read in GPIO. The press is
    reported once, from GPIO; the next interrupt captures the same level."""
    dev.set_iocon(0x01)
    events = []
    register_dpad(drv, dev, events)
    chip.press(DOWN)

    def on_read(reg):
        if reg == INTCAP and chip.pins & (1 << UP):  # UP still released
            chip.press(UP)

    chip.on_read = on_read
    dev.interrupt_event()
    chip.on_read = None
    assert chip.regs[INTF] == 1 << UP
    assert events == [("DOWN", 0, 0), ("UP", 0, 0)]
    dev.interrupt_event()
    assert events == [("DOWN", 0, 0), ("UP", 0, 0)]
    chip.release(UP)
    dev.interrupt_event()
    assert events == [("DOWN", 0, 0), ("UP", 0, 0), ("UP", 1, 1)]


def test_falling_only_filters_changes_found_in_gpio(drv, dev, chip):
    events = []
    up = dpad_pin(drv, dev, UP)
    down = dpad_pin(drv, dev, DOWN)
    up.irq(recorder(events, "UP"), BOTH)
    down.irq(recorder(events, "DOWN"), down.IRQ_FALLING)
    chip.press(UP)
    chip.press(DOWN)  # missed by the chip, found in GPIO
    dev.interrupt_event()
    chip.release(UP)
    chip.release(DOWN)  # missed by the chip, found in GPIO
    dev.interrupt_event()
    assert events == [("UP", 0, 0), ("DOWN", 0, 0), ("UP", 1, 1)]


def test_rising_only_filters_changes_found_in_gpio(drv, dev, chip):
    events = []
    up = dpad_pin(drv, dev, UP)
    down = dpad_pin(drv, dev, DOWN)
    up.irq(recorder(events, "UP"), BOTH)
    down.irq(recorder(events, "DOWN"), down.IRQ_RISING)
    chip.press(UP)
    chip.press(DOWN)  # missed by the chip, found in GPIO
    dev.interrupt_event()
    chip.release(UP)
    chip.release(DOWN)  # missed by the chip, found in GPIO
    dev.interrupt_event()
    assert events == [("UP", 0, 0), ("UP", 1, 1), ("DOWN", 1, 1)]


def test_device_callbacks_get_changes_found_in_gpio(drv, dev, chip):
    calls = []
    dpad_pin(drv, dev, UP)
    dpad_pin(drv, dev, LEFT)
    dev.interrupt_on_change(UP, lambda level: calls.append(("UP", level)))
    dev.interrupt_on_falling(LEFT, lambda: calls.append("fall"))
    dev.interrupt_on_rising(LEFT, lambda: calls.append("rise"))
    chip.press(UP)
    chip.press(LEFT)
    chip.release(LEFT)
    chip.press(LEFT)  # pressed at the service, after a missed tap
    dev.interrupt_event()
    assert calls == [("UP", 0), "fall"]


def test_registration_takes_held_level_without_event(drv, dev, chip):
    events = []
    btn = dpad_pin(drv, dev, LEFT)
    chip.press(LEFT)  # held before the registration
    btn.irq(recorder(events, "LEFT"), BOTH)
    other = dpad_pin(drv, dev, UP)
    other.irq(recorder(events, "UP"), BOTH)
    chip.press(UP)
    dev.interrupt_event()
    assert events == [("UP", 0, 0)]
    chip.release(LEFT)
    dev.interrupt_event()
    assert events == [("UP", 0, 0), ("LEFT", 1, 1)]


def test_registration_takes_released_level_without_event(drv, dev, chip):
    events = []
    register_dpad(drv, dev, events)
    chip.press(DOWN)
    dev.interrupt_event()
    assert events == [("DOWN", 0, 0)]


def test_registration_during_pending_interrupt_takes_level(drv, dev, chip):
    """UP is registered while a DOWN press is pending and UP is held: the
    DOWN press is reported, UP gets its level and no event."""
    events = []
    down = dpad_pin(drv, dev, DOWN)
    up = dpad_pin(drv, dev, UP)
    down.irq(recorder(events, "DOWN"), BOTH)
    chip.press(DOWN)
    chip.press(UP)
    up.irq(recorder(events, "UP"), BOTH)
    dev.interrupt_event()
    assert events == [("DOWN", 0, 0)]
    chip.release(UP)
    dev.interrupt_event()
    assert events == [("DOWN", 0, 0), ("UP", 1, 1)]


def test_disable_interrupt_stops_changes_found_in_gpio(drv, dev, chip):
    events = []
    up = dpad_pin(drv, dev, UP)
    down = dpad_pin(drv, dev, DOWN)
    up.irq(recorder(events, "UP"), BOTH)
    down.irq(recorder(events, "DOWN"), BOTH)
    dev.disable_interrupt(UP)
    # A callback put back by hand does not make UP enabled again.
    dev.events_change[UP] = lambda level: events.append(("UP", level))
    chip.press(DOWN)
    chip.press(UP)
    dev.interrupt_event()
    chip.release(UP)
    chip.release(DOWN)
    dev.interrupt_event()
    assert events == [("DOWN", 0, 0), ("DOWN", 1, 1)]


def test_disable_with_pending_interrupt_reports_nothing(drv, dev, chip):
    events = []
    btn = dpad_pin(drv, dev, UP)
    btn.irq(recorder(events, "UP"), BOTH)
    chip.press(UP)  # pending
    dev.disable_interrupt(UP)
    dev.interrupt_event()
    assert events == []


def test_pin_not_interrupt_enabled_is_never_reported(drv, dev, chip):
    events = []
    down = dpad_pin(drv, dev, DOWN)
    dpad_pin(drv, dev, LEFT)
    down.irq(recorder(events, "DOWN"), BOTH)
    # A callback stored without enabling the interrupt of LEFT.
    dev.events_change[LEFT] = lambda level: events.append(("LEFT", level))
    chip.press(DOWN)
    chip.press(LEFT)
    dev.interrupt_event()
    chip.release(LEFT)
    chip.release(DOWN)
    dev.interrupt_event()
    assert events == [("DOWN", 0, 0), ("DOWN", 1, 1)]


def test_reenabled_pin_takes_its_level_again(drv, dev, chip):
    events = []
    btn = dpad_pin(drv, dev, UP)
    btn.irq(recorder(events, "UP"), BOTH)
    dev.disable_interrupt(UP)
    chip.press(UP)  # not reported: disabled
    btn.irq(recorder(events, "UP"), BOTH)
    dev.interrupt_event()
    assert events == []
    chip.release(UP)
    dev.interrupt_event()
    assert events == [("UP", 1, 1)]


def test_soft_irq_during_dispatch_reports_each_change_once(drv, dev, chip):
    """A soft IRQ that runs while the handlers of an earlier service are
    called (registration from main code) compares with the levels already
    updated: no event twice, none lost."""
    events = []
    down = dpad_pin(drv, dev, DOWN)
    up = dpad_pin(drv, dev, UP)
    left = dpad_pin(drv, dev, LEFT)
    nested = []

    def on_down(pin):
        events.append(("DOWN", pin.irq_level()))
        if not nested:
            nested.append(1)
            chip.release(DOWN)
            dev.interrupt_event()  # soft IRQ at a jump of the dispatch

    down.irq(on_down, BOTH)
    up.irq(recorder(events, "UP"), BOTH)
    chip.press(DOWN)
    chip.press(UP)  # missed by the chip, found in GPIO
    left.irq(recorder(events, "LEFT"), BOTH)  # services the DOWN press
    dev.interrupt_event()
    # The DOWN release comes from the nested service: it is reported after
    # the UP press still queued by the outer one.
    assert events == [("DOWN", 0), ("UP", 0, 0), ("DOWN", 1)]


# ----- Services nested in a dispatch -----


def test_nested_registration_keeps_order_of_queued_changes(drv, dev, chip):
    """LEFT is pressed, UP is pressed while LEFT is pending (missed by the
    chip, found in GPIO) and released just after the GPIO read. The LEFT
    handler registers DOWN: the UP release, read by that registration, comes
    after the UP press."""
    events = []
    left = dpad_pin(drv, dev, LEFT)
    up = dpad_pin(drv, dev, UP)
    down = dpad_pin(drv, dev, DOWN)

    def on_left(pin):
        events.append(("LEFT", pin.irq_level()))
        down.irq(recorder(events, "DOWN"), BOTH)

    left.irq(on_left, BOTH)
    up.irq(recorder(events, "UP"), BOTH)
    chip.press(LEFT)
    chip.press(UP)  # missed by the chip

    def on_read(reg):
        if reg == GPIO:
            chip.on_read = None
            chip.release(UP)  # after the read: raises a new interrupt

    chip.on_read = on_read
    dev.interrupt_event()
    assert events == [("LEFT", 0), ("UP", 0, 1), ("UP", 1, 1)]
    dev.interrupt_event()
    assert events == [("LEFT", 0), ("UP", 0, 1), ("UP", 1, 1)]


def test_soft_irq_during_registration_keeps_order(drv, dev, chip):
    """Same as above, with the registration made from main code and the
    soft IRQ of the UP release run at a jump of the dispatch."""
    events = []
    left = dpad_pin(drv, dev, LEFT)
    up = dpad_pin(drv, dev, UP)
    down = dpad_pin(drv, dev, DOWN)

    def on_left(pin):
        events.append(("LEFT", pin.irq_level()))
        dev.interrupt_event()  # the soft IRQ of the UP release

    left.irq(on_left, BOTH)
    up.irq(recorder(events, "UP"), BOTH)
    chip.press(LEFT)
    chip.press(UP)  # missed by the chip

    def on_read(reg):
        if reg == GPIO:
            chip.on_read = None
            chip.release(UP)

    chip.on_read = on_read
    down.irq(recorder(events, "DOWN"), BOTH)
    assert events == [("LEFT", 0), ("UP", 0, 1), ("UP", 1, 1)]


def test_release_during_dispatch_comes_after_queued_press(drv, dev, chip):
    """DOWN is pending and LEFT is pressed but missed. The DOWN handler
    releases LEFT, then registers UP: the LEFT press, then its release."""
    events = []
    down = dpad_pin(drv, dev, DOWN)
    left = dpad_pin(drv, dev, LEFT)
    up = dpad_pin(drv, dev, UP)

    def on_down(pin):
        events.append(("DOWN", pin.irq_level()))
        chip.release(LEFT)
        up.irq(recorder(events, "UP"), BOTH)

    down.irq(on_down, BOTH)
    left.irq(recorder(events, "LEFT"), BOTH)
    chip.press(DOWN)
    chip.press(LEFT)  # missed by the chip
    dev.interrupt_event()
    assert events == [("DOWN", 0), ("LEFT", 0, 1), ("LEFT", 1, 1)]
    chip.press(LEFT)
    dev.interrupt_event()
    assert events[-1] == ("LEFT", 0, 0)
    assert len(events) == 4


def test_reregistration_in_handler_drops_queued_events(drv, dev, chip):
    """A tap before the new irq() call does not reach the new handler, even
    when its release is still queued by the service that is running."""
    first = []
    second = []
    btn = dpad_pin(drv, dev, UP)

    def on_first(pin):
        first.append(pin.irq_level())
        btn.irq(recorder(second, "second"), BOTH)

    btn.irq(on_first, BOTH)
    chip.press(UP)
    chip.release(UP)
    dev.interrupt_event()
    assert first == [0]
    assert second == []
    chip.press(UP)
    dev.interrupt_event()
    assert first == [0]
    assert second == [("second", 0, 0)]


def test_soft_irq_during_registration_dispatch_reports_new_pin(drv, dev, chip):
    """DOWN is pending when main code registers UP; the soft IRQ of an UP
    press runs in the DOWN handler. The press and the release of UP are
    both reported."""
    events = []
    down = dpad_pin(drv, dev, DOWN)
    up = dpad_pin(drv, dev, UP)

    def on_down(pin):
        events.append(("DOWN", pin.irq_level()))
        if pin.irq_level() == 0:
            chip.press(UP)
            dev.interrupt_event()

    down.irq(on_down, BOTH)
    chip.press(DOWN)
    up.irq(recorder(events, "UP"), BOTH)
    assert events == [("DOWN", 0), ("UP", 0, 0)]
    chip.release(UP)
    dev.interrupt_event()
    assert events == [("DOWN", 0), ("UP", 0, 0), ("UP", 1, 1)]


def test_handler_exception_does_not_block_later_events(drv, dev, chip):
    events = []
    btn = dpad_pin(drv, dev, UP)

    def handler(pin):
        events.append(pin.irq_level())
        if len(events) == 1:
            raise RuntimeError("handler")

    btn.irq(handler, BOTH)
    chip.press(UP)
    with pytest.raises(RuntimeError):
        dev.interrupt_event()
    chip.release(UP)
    dev.interrupt_event()
    assert events == [0, 1]


def test_handler_exception_still_delivers_nested_events(drv, dev, chip):
    """The UP handler raises after a soft IRQ queued a DOWN press. That read
    already cleared the interrupt, so no later interrupt would deliver the
    press: the same service delivers it, then the exception reaches the
    caller."""
    events = []
    up = dpad_pin(drv, dev, UP)
    down = dpad_pin(drv, dev, DOWN)

    def on_up(pin):
        events.append(("UP", pin.irq_level()))
        chip.press(DOWN)
        dev.interrupt_event()  # soft IRQ at a jump of the handler
        raise RuntimeError("handler")

    up.irq(on_up, BOTH)
    down.irq(recorder(events, "DOWN"), BOTH)
    chip.press(UP)
    with pytest.raises(RuntimeError, match="handler"):
        dev.interrupt_event()
    assert events == [("UP", 0), ("DOWN", 0, 0)]
    assert chip.regs[INTF] == 0
    assert dev._head == dev._tail


def test_first_handler_exception_is_raised_after_all_events(drv, dev, chip):
    """Two handlers of the same read raise: both run, and the first
    exception reaches the caller once every event is delivered."""
    events = []
    up = dpad_pin(drv, dev, UP)
    down = dpad_pin(drv, dev, DOWN)

    def failing(name):
        def handler(pin):
            events.append((name, pin.irq_level()))
            raise RuntimeError(name)

        return handler

    up.irq(failing("UP"), BOTH)
    down.irq(failing("DOWN"), BOTH)
    chip.press(UP)
    chip.press(DOWN)  # missed by the chip, found in GPIO
    with pytest.raises(RuntimeError, match="UP"):
        dev.interrupt_event()
    assert events == [("UP", 0), ("DOWN", 0)]
    chip.release(UP)
    with pytest.raises(RuntimeError, match="UP"):
        dev.interrupt_event()
    assert events[-1] == ("UP", 1)


def test_many_services_during_a_slow_handler_lose_no_level(drv, dev, chip):
    """More nested services than the queue holds: the changes that found no
    room are read again from GPIO once the queue is empty, so the last
    reported level is the real one."""
    events = []
    up = dpad_pin(drv, dev, UP)
    down = dpad_pin(drv, dev, DOWN)
    taps = []

    def on_up(pin):
        events.append(("UP", pin.irq_level()))
        if not taps:
            for _ in range(20):
                taps.append(1)
                chip.press(DOWN)
                dev.interrupt_event()
                chip.release(DOWN)
                dev.interrupt_event()
            chip.press(DOWN)
            dev.interrupt_event()

    up.irq(on_up, BOTH)
    down.irq(recorder(events, "DOWN"), BOTH)
    chip.press(UP)
    dev.interrupt_event()
    downs = [e[1] for e in events if e[0] == "DOWN"]
    # Levels alternate and the last one is the real level: pressed.
    assert all(a != b for a, b in pairwise(downs))
    assert downs[0] == 0
    assert downs[-1] == 0
    assert dev._overflow == 0
    chip.release(DOWN)
    dev.interrupt_event()
    downs = [e[1] for e in events if e[0] == "DOWN"]
    assert all(a != b for a, b in pairwise(downs))
    assert downs[-1] == 1


# ----- Re-registration and reset -----


def test_switch_from_both_edges_to_falling_only(drv, dev, chip):
    events = []
    btn = dpad_pin(drv, dev, UP)
    btn.irq(recorder(events, "UP"), BOTH)
    btn.irq(recorder(events, "UP"), btn.IRQ_FALLING)
    chip.press(UP)
    dev.interrupt_event()
    chip.release(UP)
    dev.interrupt_event()
    assert events == [("UP", 0, 0)]


def test_active_low_irq_defaults_to_both_edges(drv, dev, chip):
    pin_cls = drv.active_low_pin.MCP23009ActiveLowPin
    btn = pin_cls(dev, UP, pin_cls.IN, pin_cls.PULL_UP)
    events = []
    btn.irq(recorder(events, "UP"))
    chip.press(UP)
    dev.interrupt_event()
    chip.release(UP)
    dev.interrupt_event()
    assert events == [("UP", 1, 1), ("UP", 0, 0)]


def test_soft_reset_forgets_enabled_pins(drv, dev, chip):
    events = []
    up = dpad_pin(drv, dev, UP)
    up.irq(recorder(events, "UP"), BOTH)
    dev._soft_reset()
    down = dpad_pin(drv, dev, DOWN)
    down.irq(recorder(events, "DOWN"), BOTH)
    chip.press(DOWN)
    chip.press(UP)  # no longer watched
    dev.interrupt_event()
    assert events == [("DOWN", 0, 0)]


def test_hardware_reset_forgets_enabled_pins(drv, dev, chip):
    events = []
    up = dpad_pin(drv, dev, UP)
    up.irq(recorder(events, "UP"), BOTH)
    dev.reset()
    chip.regs[GPINTEN] = 0  # what the reset pulse does to the chip
    down = dpad_pin(drv, dev, DOWN)
    down.irq(recorder(events, "DOWN"), BOTH)
    chip.press(DOWN)
    chip.press(UP)  # no longer watched
    dev.interrupt_event()
    assert events == [("DOWN", 0, 0)]
