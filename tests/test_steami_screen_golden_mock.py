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
checkerboards); no other entry changed. The graph_empty_nan entry was added
when graph() drew "--" for an empty history or a NaN last value (#463); the
graph entry gained only that "--" call for its graph([]) case.

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
NAN = float("nan")

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
    "graph_empty_nan": lambda s: (
        s.graph([], min_val=0, max_val=100, color=5),
        s.graph([10, 30, NAN], color=5),
        s.graph([10, NAN, 30, 70], color=5),
        s.graph([NAN, NAN, NAN], color=5),
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
    return record(SCRIPTS[widget_name])


def record(script):
    """Replay script(screen) on a 128x128 raw display behind SSD1327Display."""
    module, _ = load_driver_mock("steami_screen", None)
    try:
        fake_framebuf = types.ModuleType("framebuf")
        fake_framebuf.MONO_HLSB = 3
        fake_framebuf.FrameBuffer = _GlyphFrameBuffer
        sys.modules["framebuf"] = fake_framebuf
        raw = RawDisplay()
        display = sys.modules["steami_screen"].SSD1327Display(raw)
        script(module.Screen(display))
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


# graph() with an empty history or NaN values (#463, Arduino 5.9: "-- if NAN",
# "0 or 1 point draws the frame and the value only", "NAN points are skipped
# (gap in the curve)"). Box x 21, y 38, w 92, h 52 on 128; the value text
# WHITE (15) centred on cx 64 at row 31, so a 2-character text at x 56, as
# "90" in the graph entry. The curve is drawn in colour 5.
FRAME_128 = (["line", 21, 38, 21, 90, 6], ["line", 21, 90, 112, 90, 6])


def _values(calls):
    return [c for c in calls if c[0] == "text" and c[4] == 15]


def _curve(calls):
    return [c for c in calls if c[0] == "line" and c[5] == 5]


def test_mock_graph_empty_history_draws_frame_and_dashes_at_128():
    calls = record(lambda s: s.graph([], min_val=0, max_val=100, color=5))
    assert _values(calls) == [["text", "--", 56, 31, 15]]
    for line in FRAME_128:
        assert line in calls
    assert _curve(calls) == []


def test_mock_graph_nan_last_value_shows_dashes_at_128():
    # Points x 21, 67, 113 (step 46); 10 -> row int(90 - 5.2) = 84, 30 -> 74.
    calls = record(lambda s: s.graph([10, 30, NAN], color=5))
    assert _values(calls) == [["text", "--", 56, 31, 15]]
    assert _curve(calls) == [["line", 21, 84, 67, 74, 5]]


@pytest.mark.parametrize(("last", "row"), ((float("inf"), 38), (float("-inf"), 90)))
def test_mock_graph_infinite_last_value_shows_dashes_at_128(last, row):
    # An infinite last value has no integer part: "--", like NaN. Its point
    # is kept and clamped to the top (inf) or the bottom (-inf) of the box.
    calls = record(lambda s: s.graph([10, 30, last], color=5))
    assert _values(calls) == [["text", "--", 56, 31, 15]]
    assert _curve(calls) == [["line", 21, 84, 67, 74, 5], ["line", 67, 74, 113, row, 5]]


def test_mock_graph_nan_in_the_middle_leaves_a_gap_at_128():
    # Points x 21, 51, 82, 113 (step 92 / 3); the NaN point 1 is skipped and
    # point 0 has no neighbour left: only 30 (row 74) -> 70 (row 53) is drawn.
    calls = record(lambda s: s.graph([10, NAN, 30, 70], color=5))
    assert _values(calls) == [["text", "70", 56, 31, 15]]
    assert _curve(calls) == [["line", 82, 74, 113, 53, 5]]


def test_mock_graph_all_nan_draws_frame_and_dashes_at_128():
    calls = record(lambda s: s.graph([NAN, NAN, NAN], color=5))
    assert _values(calls) == [["text", "--", 56, 31, 15]]
    for line in FRAME_128:
        assert line in calls
    assert _curve(calls) == []


def test_mock_graph_one_point_draws_frame_and_value_at_128():
    calls = record(lambda s: s.graph([5], min_val=0, max_val=10, color=5))
    assert _values(calls) == [["text", "5", 60, 31, 15]]
    for line in FRAME_128:
        assert line in calls
    assert _curve(calls) == []


# NaN and infinity on the SSD1327 path (Arduino spec 5.11): no widget raises,
# value() and the integer labels write "--", bar and gauge stay empty, the
# compass has no needle.
INF = float("inf")


@pytest.mark.parametrize("bad", (NAN, INF, -INF), ids=("nan", "inf", "-inf"))
def test_mock_value_of_nan_or_infinity_draws_dashes_at_128(bad):
    calls = record(lambda s: s.value(bad, unit="C", label="Temp"))
    assert calls == record(lambda s: s.value("--", unit="C", label="Temp"))


def test_mock_gauge_labels_of_nan_and_infinity_are_dashes_at_128():
    calls = record(lambda s: s.gauge(50, min_val=NAN, max_val=INF, color=5))
    assert [c[1] for c in calls if c[0] == "text"] == ["--", "--"]
    # A NaN ratio leaves the gauge empty: no call in colour 5.
    assert not [c for c in calls if c[-1] == 5]


def test_mock_bar_and_gauge_of_nan_are_empty_at_128():
    assert record(lambda s: s.bar(NAN, color=5)) == record(lambda s: s.bar(0, color=5))
    assert record(lambda s: s.bar(-50, max_val=-100, color=5)) == record(
        lambda s: s.bar(0, color=5)
    )
    assert record(lambda s: s.gauge(NAN, color=5)) == record(lambda s: s.gauge(0, color=5))


@pytest.mark.parametrize("bad", (NAN, INF, -INF), ids=("nan", "inf", "-inf"))
def test_mock_compass_of_nan_or_infinity_has_no_needle_at_128(bad):
    calls = record(lambda s: s.compass(bad, color=5))
    assert calls
    assert not [c for c in calls if c[-1] == 5]
