"""Tests of steami.tone(), steami.no_tone() and the pad constants (steami.buzzer, steami.const)."""

import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


class FakeChannel:
    def __init__(self, pin):
        self.pin = pin
        self.duty = None

    def pulse_width_percent(self, value):
        self.duty = value


class FakeTimer:
    """pyb.Timer: only what the buzzer uses."""

    PWM = "PWM"
    created = []

    def __init__(self, timer_id, freq=None):
        self.id = timer_id
        self.frequency = freq
        self.channels = {}
        FakeTimer.created.append(self)

    def freq(self, value):
        self.frequency = value

    def channel(self, number, mode, pin=None):
        assert mode == FakeTimer.PWM
        ch = FakeChannel(pin)
        self.channels[number] = ch
        return ch


class FakeSoftTimer:
    """machine.Timer: a one-shot soft timer fired by the test."""

    ONE_SHOT = 0
    PERIODIC = 1
    armed = []

    def __init__(self, timer_id=-1, mode=PERIODIC, period=-1, callback=None):
        assert timer_id == -1
        self.mode = mode
        self.period = period
        self.callback = callback
        self.active = True
        FakeSoftTimer.armed.append(self)

    def deinit(self):
        self.active = False

    def fire(self):
        if self.active:
            self.active = False
            self.callback(self)

    def fire_late(self):
        """Run the callback even after deinit(), as a scheduled callback does.

        A soft timer queues its callback with mp_sched_schedule(): deinit()
        cannot take back a callback already queued when the timer expired.
        """
        self.active = False
        self.callback(self)


@pytest.fixture
def steami(monkeypatch):
    """The steami package with fake pyb and machine modules."""
    from tests.fake_machine import FakePin, micropython_stub

    FakeTimer.created = []
    FakeSoftTimer.armed = []
    pyb = types.ModuleType("pyb")
    pyb.Timer = FakeTimer
    pyb.Pin = FakePin
    machine = types.ModuleType("machine")
    machine.Pin = FakePin
    machine.Timer = FakeSoftTimer
    monkeypatch.setitem(sys.modules, "pyb", pyb)
    monkeypatch.setitem(sys.modules, "machine", machine)
    monkeypatch.setitem(sys.modules, "micropython", micropython_stub)
    monkeypatch.syspath_prepend(str(ROOT / "lib" / "steami"))
    for name in list(sys.modules):
        if name == "steami" or name.startswith("steami."):
            monkeypatch.delitem(sys.modules, name)
    import steami

    yield steami
    for name in list(sys.modules):
        if name == "steami" or name.startswith("steami."):
            del sys.modules[name]


def buzzer():
    """The one Timer 1 created by the buzzer, and its channel 4."""
    assert len(FakeTimer.created) == 1
    timer = FakeTimer.created[0]
    assert timer.id == 1
    return timer, timer.channels[4]


def test_mock_tone_plays_on_timer1_channel4(steami):
    steami.tone(440)
    timer, channel = buzzer()
    assert timer.frequency == 440
    assert channel.duty == 50
    assert channel.pin._id == "SPEAKER"
    assert FakeSoftTimer.armed == []


def test_mock_no_tone_silences(steami):
    steami.tone(440)
    steami.no_tone()
    _, channel = buzzer()
    assert channel.duty == 0


def test_mock_no_tone_before_any_tone_touches_nothing(steami):
    steami.no_tone()
    assert FakeTimer.created == []


def test_mock_tone_reuses_the_timer(steami):
    steami.tone(440)
    steami.tone(880)
    timer, channel = buzzer()
    assert timer.frequency == 880
    assert channel.duty == 50


def test_mock_tone_zero_frequency_is_silence(steami):
    steami.tone(440)
    steami.tone(0)
    _, channel = buzzer()
    assert channel.duty == 0


def test_mock_tone_with_duration_stops_without_blocking(steami):
    steami.tone(440, 200)
    _, channel = buzzer()
    assert channel.duty == 50
    (stop,) = FakeSoftTimer.armed
    assert stop.mode == FakeSoftTimer.ONE_SHOT
    assert stop.period == 200
    stop.fire()
    assert channel.duty == 0


def test_mock_new_tone_cancels_the_pending_stop(steami):
    steami.tone(440, 200)
    first = FakeSoftTimer.armed[0]
    steami.tone(880)
    assert not first.active
    first.fire()
    _, channel = buzzer()
    assert channel.duty == 50


def test_mock_no_tone_cancels_the_pending_stop(steami):
    steami.tone(440, 200)
    steami.no_tone()
    assert not FakeSoftTimer.armed[0].active


def test_mock_late_stop_does_not_silence_a_newer_tone(steami):
    steami.tone(440, 100)
    stale = FakeSoftTimer.armed[0]
    steami.tone(880)
    stale.fire_late()
    _, channel = buzzer()
    assert channel.duty == 50


def test_mock_late_stop_keeps_the_newer_timed_tone_and_its_stop(steami):
    steami.tone(440, 100)
    stale = FakeSoftTimer.armed[0]
    steami.tone(880, 500)
    current = FakeSoftTimer.armed[1]
    stale.fire_late()
    _, channel = buzzer()
    assert channel.duty == 50
    assert current.active
    current.fire()
    assert channel.duty == 0


def test_mock_late_stop_after_no_tone_then_tone(steami):
    steami.tone(440, 100)
    stale = FakeSoftTimer.armed[0]
    steami.no_tone()
    steami.tone(660)
    stale.fire_late()
    _, channel = buzzer()
    assert channel.duty == 50


def _fire_in_cancel(steami, timer, at_line):
    """Trace hook: run timer's callback before the at_line-th line of _cancel().

    MicroPython runs scheduled callbacks at backward and conditional jumps
    (py/vm.c, pending_exception_check), so the stop of the current tone can
    run in the middle of _cancel(). Line boundaries cover every such jump.
    """
    code = steami.buzzer._cancel.__code__
    state = {"line": 0, "fired": False}

    def local(frame, event, arg):
        if event == "line" and not state["fired"]:
            if state["line"] == at_line:
                state["fired"] = True
                timer.fire_late()
            state["line"] += 1
        return local

    def tracer(frame, event, arg):
        if frame.f_code is code and not state["fired"]:
            return local
        return None

    return tracer, state


def _race_in_cancel(steami, action):
    """Run action() with the current stop firing at each line of _cancel()."""
    at_line = 0
    while True:
        steami.no_tone()
        steami.tone(1000, 5)
        current = FakeSoftTimer.armed[-1]
        tracer, state = _fire_in_cancel(steami, current, at_line)
        previous = sys.gettrace()
        sys.settrace(tracer)
        try:
            action()
        finally:
            sys.settrace(previous)
        if not state["fired"]:
            return
        yield at_line
        at_line += 1


def test_mock_current_stop_firing_inside_cancel_during_tone(steami):
    lines = 0
    for _ in _race_in_cancel(steami, lambda: steami.tone(2000)):
        _, channel = buzzer()
        assert channel.duty == 50
        assert buzzer()[0].frequency == 2000
        lines += 1
    assert lines >= 3


def test_mock_current_stop_firing_inside_cancel_during_no_tone(steami):
    lines = 0
    for _ in _race_in_cancel(steami, steami.no_tone):
        _, channel = buzzer()
        assert channel.duty == 0
        lines += 1
    assert lines >= 3


def test_mock_pad_constants(steami):
    # GP0..GP3 of the MCP23009E (wiki: hardware/main-components/buttons-audio).
    assert steami.PAD_P28 == 0
    assert steami.PAD_P29 == 1
    assert steami.PAD_P24 == 2
    assert steami.PAD_P25 == 3
    from steami.const import PAD_P24

    assert PAD_P24 == 2
