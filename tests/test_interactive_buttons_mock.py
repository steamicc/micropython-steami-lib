"""Runs the interactive Buttons check (tests/interactive/steami_buttons.py) against the fakes.

A simulated tester does what each step asks as soon as the screen shows
"À vous !", on the board timeline of ButtonsRig: every step must pass. This
keeps the script, which only a human runs on a board, free of mistakes.
"""

import sys
import time
from pathlib import Path

import pytest

from tests.fake_machine import FakePin
from tests.fake_machine.mcp23009 import DOWN, LEFT, RIGHT, UP
from tests.test_steami_functions_mock import (  # noqa: F401 (fixtures)
    ButtonsRig,
    board_module,
    steami,
)

SCRIPT = Path(__file__).parent / "interactive" / "steami_buttons.py"
ARROWS = {"UP": UP, "DOWN": DOWN, "LEFT": LEFT, "RIGHT": RIGHT}
LINES = {"A_BUTTON": 7, "B_BUTTON": 8, "MENU_BUTTON": 0}  # all on port A
# The button each tap step asks for.
TAPPED = dict(
    zip(range(4, 15), ("A", "B", "MENU", "UP", "DOWN", "LEFT", "RIGHT", "A", "B", "UP", "UP"))
)


class ArmedRegisters:
    """mem32 of a board whose EXTI lines are routed to port A and armed."""

    def __getitem__(self, addr):
        if 0x40010008 <= addr <= 0x40010014:  # SYSCFG_EXTICR: port A
            return 0
        return 0xFFFFFFFF


class Finger:
    """Does what the step on the screen asks, as soon as it shows "À vous !"."""

    def __init__(self, rig):
        self.rig = rig
        self.title = ""

    def act(self, step):
        rig = self.rig
        t = rig.now + 300
        if step == 1:
            rig.tap_at(t, "MENU", 80)
        elif 4 <= step <= 14:
            fast = step in (11, 12)  # two or three taps a second
            name = TAPPED[step]
            for k in range(10):
                at = t + k * (400 if fast else 1000) + 37 * (k % 3)
                if step == 14:  # at each number of the metronome, 150 ms late
                    at = rig.now + 150 + k * 700
                if name in ARROWS:
                    rig.dpad_tap_at(at, ARROWS[name], 80)
                else:
                    rig.tap_at(at, name, 80)
        elif step in (15, 16):
            for k in range(10):
                if step == 15:
                    rig.tap_at(t + k * 3000, "A", 2000)
                else:
                    rig.dpad_tap_at(t + k * 3000, UP, 2000)
        elif step == 17:
            for k in range(200):
                rig.dpad_tap_at(t + k * 250, tuple(ARROWS.values())[k % 4], 60 + k % 50)


def make_screen(tester):
    class Screen:
        def begin(self):
            return True

        def title(self, text, *args, **kwargs):
            tester.title = text

        def text(self, text, *args, **kwargs):
            if text == "À vous !":
                tester.act(int(tester.title.split()[1].split("/")[0]))

        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    return Screen


def run_script(steami, monkeypatch, step, capsys):  # noqa: F811
    rig = ButtonsRig(steami, monkeypatch)
    rig.read_us = 400
    tester = Finger(rig)
    import steami as package

    stub = type(sys)("steami_screen")
    stub.Screen = object
    for color in ("GREEN", "LIGHT", "RED", "WHITE", "YELLOW"):
        setattr(stub, color, color)
    monkeypatch.setitem(sys.modules, "steami_screen", stub)
    monkeypatch.setattr(package, "Screen", make_screen(tester))
    machine = sys.modules["machine"]
    monkeypatch.setattr(machine, "mem32", ArmedRegisters(), raising=False)
    monkeypatch.setattr(FakePin, "pin", lambda self: LINES[self._id], raising=False)
    monkeypatch.setattr(FakePin, "port", lambda self: 0, raising=False)
    monkeypatch.setattr(time, "ticks_ms", lambda: rig.now)
    monkeypatch.setattr(time, "ticks_diff", lambda a, b: a - b)
    monkeypatch.setattr(time, "ticks_add", lambda a, b: a + b, raising=False)
    monkeypatch.setattr(time, "sleep_ms", rig.advance)
    monkeypatch.setattr(sys, "print_exception", print, raising=False)
    import steami.buttons as buttons_module

    # The rig's pins: Pin("A_BUTTON") is the object Buttons uses.
    monkeypatch.setattr(machine, "Pin", buttons_module.Pin)
    code = compile(SCRIPT.read_text(encoding="utf-8"), str(SCRIPT), "exec")
    exec(code, {"__name__": "__main__", "STEP": step})  # noqa: S102
    return capsys.readouterr().out


@pytest.mark.parametrize("step", range(1, 18))
def test_mock_interactive_buttons_step_passes_with_a_careful_tester(
    steami,  # noqa: F811
    monkeypatch,
    capsys,
    step,
):
    out = run_script(steami, monkeypatch, step, capsys)
    assert "1/1 steps passed" in out, out
