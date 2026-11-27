"""Golden test: the 128 px drawing calls of every steami_screen widget.

The calls are recorded at the raw driver level: a recording raw display is
wrapped in the real SSD1327Display, inside a Screen. The recorded colours are
the grey4 ints the panel receives, and the scaled text goes through
SSD1327Display.draw_scaled_text. The reference JSON was recorded before the
GC9A01 scaling rule. The SSD1327 output may change only to improve the
drawing, and every change to the 128 px golden is justified: the gauge entry
was re-recorded when the arc became a scanline ring sector (solid rings, about
60 edge pixels per call changed). The accents entry was added when accented
letters were folded to one 8x8 cell (they were two checkerboards, 16 px, for
one counted cell) and '°' drawn with the Arduino 8x8 degree glyph (it was two
checkerboards); no other entry changed.

Regenerate (only on purpose): STEAMI_GOLDEN_WRITE=1 python3 -m pytest <this file>
The writer rewrites every entry the same way, so `git diff` must show only the
entries meant to change.
"""

import json
import os
import sys
import types
from pathlib import Path

import pytest

from tests.runner.executor import cleanup_driver, load_driver_mock

GOLDEN = Path(__file__).parent / "golden" / "steami_screen_128.json"


class RawDisplay:
    """Records every raw drawing call (what an SSD1327 driver would receive)."""

    def __init__(self):
        self.calls = []
        self.width = 128
        self.height = 128

    def fill(self, color):
        self.calls.append(("fill", color))

    def pixel(self, x, y, color):
        self.calls.append(("pixel", x, y, color))

    def text(self, text, x, y, color):
        self.calls.append(("text", text, x, y, color))

    def line(self, x1, y1, x2, y2, color):
        self.calls.append(("line", x1, y1, x2, y2, color))

    def fill_rect(self, x, y, w, h, color):
        self.calls.append(("fill_rect", x, y, w, h, color))

    def rect(self, x, y, w, h, color):
        self.calls.append(("rect", x, y, w, h, color))

    def show(self):
        self.calls.append(("show",))


class _GlyphFrameBuffer:
    """Tiny MONO_HLSB framebuf: text() lights a deterministic pattern per char.

    Test-local on purpose: the shared stub draws no glyph, and this keeps the
    golden independent of any later stub change.
    """

    def __init__(self, buffer, width, height, fmt):
        self.pixels = {}

    def fill(self, col):
        self.pixels = {}

    def text(self, string, x, y, col=1):
        code = ord(string[0])
        for py in range(8):
            for px in range(8):
                if (code * (px + 1) + py * 3) % 3 == 0:
                    self.pixels[(x + px, y + py)] = col

    def pixel(self, x, y, col=None):
        return self.pixels.get((x, y), 0)


AT_POSITIONS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW", "CENTER")
FACES = ("happy", "sad", "surprised", "sleeping", "angry", "love")

# Each script receives a Screen and draws with fixed arguments.
SCRIPTS = {
    "title": lambda s: (s.title("Hello"), s.title("A long title here", color=5)),
    "value": lambda s: (
        s.value(23.5),
        s.value(42, unit="C"),
        s.value(7, unit="%", label="Hum", color=3),
        s.value(1, at="W"),
        s.value(2, at="E", unit="cm"),
        s.value(3, at="N"),
        s.value(88, scale=3, y_offset=5),
        s.value(5, unit="V", y_offset=-10, scale=1),
    ),
    "subtitle": lambda s: (
        s.subtitle("one line"),
        s.subtitle("first", "second"),
        s.subtitle("a", "bb", "ccc", color=3),
        s.subtitle(),
    ),
    "bar": lambda s: (
        s.bar(0),
        s.bar(50),
        s.bar(100, y_offset=12, color=5),
        s.bar(150, max_val=100),
        s.bar(3, max_val=0),
    ),
    "gauge": lambda s: (
        s.gauge(0),
        s.gauge(50),
        s.gauge(100, color=5),
        s.gauge(-5, min_val=-10, max_val=40),
        s.gauge(25, arc_width=8),
        s.gauge(1500, min_val=0, max_val=3000),
    ),
    "graph": lambda s: (
        s.graph([10, 30, 20, 70, 55, 90]),
        s.graph([5], min_val=0, max_val=10),
        s.graph([], min_val=0, max_val=2000),
        s.graph([0, 1000, 2000], min_val=0, max_val=2000, color=5),
    ),
    "menu": lambda s: (
        s.menu(["Temperature", "Humidity", "Pressure"], selected=1),
        s.menu(["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"], selected=7),
        s.menu(["Only"], selected=0, color=5),
    ),
    "compass": lambda s: (s.compass(0), s.compass(45), s.compass(200, color=5)),
    "watch": lambda s: (
        s.watch(10, 10),
        s.watch(3, 45, 30),
        s.watch(23, 59, 59, color=5),
    ),
    "face_normal": lambda s: [s.face(name) for name in FACES],
    "face_compact": lambda s: [s.face(name, compact=True, color=5) for name in FACES],
    "face_bitmap": lambda s: (
        s.face((0x3C, 0x42, 0xA5, 0x81, 0xA5, 0x99, 0x42, 0x3C)),
        s.face("unknown"),
    ),
    "text_at": lambda s: [s.text("Hi", at=at) for at in AT_POSITIONS],
    "text_at_scaled": lambda s: [s.text("Hi", at=at, scale=2, color=3) for at in AT_POSITIONS],
    "text_xy": lambda s: (
        s.text("xy", at=(10, 20)),
        s.text("big", at=(30, 40), scale=3, color=5),
        s.text("", at="N"),
    ),
    "line": lambda s: (s.line(0, 0, 127, 127), s.line(10, 20, 100, 20, color=3)),
    "circle": lambda s: (
        s.circle(64, 64, 30),
        s.circle(40, 50, 10, color=3, fill=True),
        s.circle(100, 100, 0),
    ),
    "rect": lambda s: (
        s.rect(10, 10, 50, 30),
        s.rect(20, 60, 40, 20, color=3, fill=True),
    ),
    "pixel": lambda s: (s.pixel(5, 6), s.pixel(127, 127, 3)),
    "clear": lambda s: (s.clear(), s.clear(7), s.show()),
    "accents": lambda s: (
        s.title("Été"),
        s.subtitle("élève", "Ÿ"),
        s.text("23°C", at="NE"),
        s.value("Été", unit="°C"),
        s.value(21.5, unit="°C", label="Températ"),
        s.menu(["Réglages", "Données"], selected=0),
        s.text("°", at=(3, 100), scale=2),
    ),
}


def _jsonable(value):
    if isinstance(value, (tuple, list)):
        return [_jsonable(v) for v in value]
    return value


def record_calls(widget_name):
    """Replay the scripted calls of one widget on a 128x128 raw display behind SSD1327Display."""
    module, _ = load_driver_mock("steami_screen", None)
    try:
        fake_framebuf = types.ModuleType("framebuf")
        fake_framebuf.MONO_HLSB = 3
        fake_framebuf.FrameBuffer = _GlyphFrameBuffer
        sys.modules["framebuf"] = fake_framebuf
        raw = RawDisplay()
        display = sys.modules["steami_screen"].SSD1327Display(raw)
        SCRIPTS[widget_name](module.Screen(display))
        return [_jsonable(call) for call in raw.calls]
    finally:
        cleanup_driver("steami_screen")


def _write_golden():
    data = {name: record_calls(name) for name in SCRIPTS}
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for name, calls in data.items():
        body = ",\n".join("  " + json.dumps(call) for call in calls)
        lines.append(f"{json.dumps(name)}: [\n{body}\n]")
    GOLDEN.write_text("{\n" + ",\n".join(lines) + "\n}\n")


if os.environ.get("STEAMI_GOLDEN_WRITE") == "1":
    _write_golden()


@pytest.mark.parametrize("widget", sorted(SCRIPTS))
def test_mock_ssd1327_output_unchanged(widget):
    golden = json.loads(GOLDEN.read_text())
    calls = record_calls(widget)
    assert calls, "script drew nothing"
    assert calls == golden[widget]


def test_mock_golden_covers_every_script():
    assert set(json.loads(GOLDEN.read_text())) == set(SCRIPTS)
