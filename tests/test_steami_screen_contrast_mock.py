"""Mock tests of the grey minimum contrast of the steami_screen widgets (#437).

Arduino display design, section 5.10: on a grey panel, a widget foreground
drawn over the widget's own background is lifted to at least that background
+ STEAMI_MIN_CONTRAST (4) grey4 levels, capped at 15. The cases are the bar
fill over its GRID_DARK track (grey4 3), the gauge fill over its DARK track
(6) and the selected menu text over its DARK bar (6). BLUE is grey4 6, as
DARK, so it becomes 7 on the bar and 10 on the gauge; RED (8) becomes 10 on
the gauge. A colour panel keeps every colour, and primitives never adjust
colours.

On 128 px the calls are recorded at the raw driver level behind the real
SSD1327Display (grey4 ints), as in test_steami_screen_golden_mock.py. On
240 px the pixels are read from the real gc9a01 driver frame (palette
indexes).
"""

import sys

import pytest

from tests.fake_machine import FakePin, FakeSPI
from tests.runner.executor import cleanup_driver, load_driver_mock
from tests.test_steami_screen_golden_mock import RawDisplay, record

# steami_screen.const colours (RGB) and their grey4 level on the SSD1327.
BLACK, GRID_DARK, DARK, GRAY = (0, 0, 0), (51, 51, 51), (102, 102, 102), (153, 153, 153)
LIGHT, WHITE = (187, 187, 187), (255, 255, 255)
GREEN, RED, BLUE = (119, 255, 119), (255, 85, 85), (85, 85, 255)


def _colours(calls, kind="fill_rect"):
    """Distinct last arguments (the grey4 colour) of the calls of one kind, in order."""
    out = []
    for c in calls:
        if c[0] == kind and c[-1] not in out:
            out.append(c[-1])
    return out


# ----- 128 px, SSD1327 (grey) -----


def test_mock_min_contrast_constant_and_grey_flags():
    load_driver_mock("steami_screen", None)
    try:
        mod = sys.modules["steami_screen"]
        assert sys.modules["steami_screen.const"].STEAMI_MIN_CONTRAST == 4
        assert mod.SSD1327Display.is_color is False
        assert mod.GC9A01Display.is_color is True
    finally:
        cleanup_driver("steami_screen")


def test_mock_bar_track_is_grid_dark_and_blue_fill_is_lifted_at_128():
    # Track first (grey4 3), then the fill: BLUE (6) lifted to 3 + 4 = 7.
    assert _colours(record(lambda s: s.bar(50, color=BLUE))) == [3, 7]


@pytest.mark.parametrize(("color", "level"), ((LIGHT, 11), (RED, 8), (GREEN, 12), (WHITE, 15)))
def test_mock_bar_fill_already_readable_is_kept_at_128(color, level):
    assert _colours(record(lambda s: s.bar(50, color=color))) == [3, level]


@pytest.mark.parametrize(
    ("color", "level"),
    ((BLUE, 10), (RED, 10), (GRAY, 10), (DARK, 10), (LIGHT, 11), (GREEN, 12), (WHITE, 15)),
)
def test_mock_gauge_fill_is_lifted_over_its_dark_track_at_128(color, level):
    # Track DARK (6), fill at least 6 + 4 = 10.
    assert _colours(record(lambda s: s.gauge(50, color=color))) == [6, level]


def test_mock_empty_gauge_and_bar_draw_only_their_track_at_128():
    assert _colours(record(lambda s: s.gauge(0, color=BLUE))) == [6]
    assert _colours(record(lambda s: s.bar(0, color=BLUE))) == [3]


def test_mock_selected_menu_text_is_lifted_over_its_bar_at_128():
    calls = record(lambda s: s.menu(["Temp", "Hum"], selected=0, color=BLUE))
    assert _colours(calls) == [6]  # the DARK highlight bar
    texts = [(c[1], c[-1]) for c in calls if c[0] == "text"]
    assert texts == [("> Temp", 10), ("  Hum", 9)]


def test_mock_primitives_never_adjust_colours_at_128():
    # rect(BLUE) on a DARK rect stays grey4 6: only widgets lift.
    calls = record(
        lambda s: (s.rect(10, 10, 40, 20, DARK, fill=True), s.rect(15, 15, 10, 5, BLUE, fill=True))
    )
    assert _colours(calls) == [6]


def test_mock_lifted_is_capped_at_white():
    out = []
    record(lambda s: out.extend((s._lifted(BLACK, WHITE), s._lifted(BLUE, GRID_DARK))))
    assert out == [WHITE, (119, 119, 119)]


def test_mock_display_without_is_color_keeps_colours():
    # A backend that does not declare is_color (a simulator, a test double)
    # gets the colours as given, as before #437.
    load_driver_mock("steami_screen", None)
    try:
        raw = RawDisplay()
        s = sys.modules["steami_screen"].Screen(raw)
        s.bar(50, color=BLUE)
        assert _colours(raw.calls) == [GRID_DARK, BLUE]
    finally:
        cleanup_driver("steami_screen")


# ----- 240 px, GC9A01 (colour) -----


@pytest.fixture
def panel():
    load_driver_mock("steami_screen", None)
    driver, _ = load_driver_mock("gc9a01", None)
    steami_screen = sys.modules["steami_screen"]

    def new():
        raw = driver.GC9A01(FakeSPI(1), FakePin("dc"), FakePin("cs"))
        return steami_screen.Screen(steami_screen.GC9A01Display(raw)), raw

    yield new
    cleanup_driver("gc9a01")
    cleanup_driver("steami_screen")


def _indexes(raw):
    """Set of the palette indexes of the non-black pixels of the GS4_HMSB frame."""
    out = set()
    for b in raw.buffer:
        out.update(v for v in (b >> 4, b & 15) if v)
    return out


def test_mock_colour_panel_keeps_widget_colours_at_240(panel):
    # Palette: GRID_DARK 1, DARK 2, GRAY 3, BLUE 8.
    s, raw = panel()
    s.bar(50, color=BLUE)
    assert _indexes(raw) == {1, 8}
    s, raw = panel()
    s.gauge(50, color=BLUE)
    assert 8 in _indexes(raw) and 2 in _indexes(raw)
    s, raw = panel()
    s.menu(["Temp", "Hum"], selected=0, color=BLUE)
    assert _indexes(raw) == {2, 3, 8}
