"""Mock tests of the steami_screen scaling rule and of the round-screen fitting.

The rule (Arduino display design, section 5.8): k = (W + 64) // 128 is the
glyph and stroke factor (1 on 128 px, 2 on 240 px), and u(v) = v * W / 128,
truncated, maps the 128 px layout units. On the 240 px round GC9A01 (k = 2)
the widgets keep their text inside the circle.

Expected 240 px numbers:
- "Arduino": copied from arduino-steami-lib
  tests/native/test_steami_screen/test_main.cpp (values printed by its
  golden_layout.py), where the MicroPython widget draws the same thing;
- "rule": derived from the section 5.8 formulas where the MicroPython widget
  has no Arduino counterpart or draws differently (the derivation is in the
  comment).

The 128 px output is pinned by test_steami_screen_golden_mock.py.
Pixels are read from the real gc9a01 driver frame (palette indexes).
"""

import math
import sys

import pytest

from tests.fake_machine import FakePin, FakeSPI
from tests.runner.executor import cleanup_driver, load_driver_mock

# Palette indexes of the gc9a01 frame.
GRID_DARK, DARK, GRAY, LIGHT, WHITE, GREEN, RED = 1, 2, 3, 4, 5, 6, 7
ANCHORS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW", "CENTER")


@pytest.fixture
def mods():
    load_driver_mock("steami_screen", None)
    module, _ = load_driver_mock("gc9a01", None)
    yield sys.modules["steami_screen"], module
    cleanup_driver("gc9a01")
    cleanup_driver("steami_screen")


@pytest.fixture
def panel(mods):
    """new(size) -> (Screen, raw driver) on a fresh black frame."""
    steami_screen, driver = mods

    def new(size=240):
        raw = driver.GC9A01(FakeSPI(1), FakePin("dc"), FakePin("cs"), width=size, height=size)
        return steami_screen.Screen(steami_screen.GC9A01Display(raw)), raw

    return new


def lit(raw):
    """{(x, y): palette index} of every non-black pixel of the GS4_HMSB frame."""
    out = {}
    row = (raw.width + 1) // 2
    for i, b in enumerate(raw.buffer):
        if b:
            y, x = divmod(i, row)
            if b >> 4:
                out[(2 * x, y)] = b >> 4
            if b & 15:
                out[(2 * x + 1, y)] = b & 15
    return out


def box(raw, color=None, y0=0, y1=10**6):
    """(x0, y0, x1, y1) of the pixels of `color` (any if None) on rows y0..y1, or None."""
    pts = [p for p, c in lit(raw).items() if (color is None or c == color) and y0 <= p[1] <= y1]
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def count(raw, color):
    return sum(1 for c in lit(raw).values() if c == color)


def outside(raw, slack=1):
    """Lit pixels farther than radius + slack from the centre (Arduino rule 7: radius + 1)."""
    r = raw.width // 2 + slack
    c = raw.width // 2
    return [p for p in lit(raw) if (p[0] - c) ** 2 + (p[1] - c) ** 2 > r * r]


# ----- k and u -----


def test_mock_k_and_u_at_128_and_240(panel):
    s128, _ = panel(128)
    s240, _ = panel(240)
    assert (s128.k, s240.k) == (1, 2)
    # Arduino test_scale_quantities.
    assert [s128.u(v) for v in (8, -12, 40)] == [8, -12, 40]
    assert [s240.u(v) for v in (8, -12, 40, 11, 4, 3, 20)] == [15, -22, 75, 20, 7, 5, 37]
    assert (s128.max_chars, s240.max_chars) == (16, 30)
    assert (s240.width, s240.height, s240.center, s240.radius) == (240, 240, (120, 120), 120)


def test_mock_layout_lengths_are_named_constants(mods):
    # The u(2) and u(4) lengths of the widgets are named in const.py (#456).
    const = sys.modules["steami_screen.const"]
    assert const.STEAMI_VALUE_LABEL_GAP == 4
    assert const.STEAMI_GAUGE_RING_INSET == 4
    assert const.STEAMI_GRAPH_LABEL_PAD == 2
    assert const.STEAMI_MENU_BAR_PAD == 2
    assert (const.STEAMI_WATCH_HOUR_HALF_W, const.STEAMI_WATCH_MINUTE_HALF_W) == (3, 2)
    source = sys.modules["steami_screen.device"].__file__
    with open(source, encoding="utf-8") as f:
        code = [line.split("#")[0] for line in f]
    assert not [line for line in code if "u(2)" in line or "u(4)" in line]


def test_mock_resolve_every_anchor_at_240(panel):
    s, _ = panel()
    # Arduino test_resolve_every_anchor: resolve(at, tw 32, f 2).
    expected = {
        "N": (104, 37),
        "NE": (186, 37),
        "E": (186, 112),
        "SE": (186, 187),
        "S": (104, 187),
        "SW": (22, 187),
        "W": (22, 112),
        "NW": (22, 37),
        "CENTER": (104, 112),
    }
    for at, xy in expected.items():
        assert s._at(at, 32, 2) == xy, at
    assert s._at("CENTER", 32, 4)[1] == 105  # u(56)
    # Arduino test_scale_quantities: marginNs(tw, f) is the N row. The cap
    # (13 advances of 8 px, 52 px of half width) is 14 < the floor 37.
    for tw, f, row in ((16, 2, 37), (176, 2, 37), (208, 2, 37), (16, 4, 67), (16, 3, 52)):
        assert s._at("N", tw, f)[1] == row, (tw, f)
    # marginEw(2) 22 and marginEw(3) 30 are the W column.
    assert (s._at("W", 0, 2)[0], s._at("W", 0, 3)[0]) == (22, 30)


# ----- text(at=...), title -----

# Arduino kHiBoxes[240]: text("Hi", at, WHITE, scale) ink boxes, scale 1 then 2.
HI_240 = {
    1: (
        (112, 39, 125, 48),
        (191, 39, 204, 48),
        (202, 114, 215, 123),
        (194, 189, 207, 198),
        (112, 189, 125, 198),
        (31, 189, 44, 198),
        (22, 114, 35, 123),
        (34, 39, 47, 48),
        (112, 114, 125, 123),
    ),
    2: (
        (104, 71, 131, 90),
        (171, 71, 198, 90),
        (171, 109, 198, 128),
        (171, 145, 198, 164),
        (104, 145, 131, 164),
        (37, 145, 64, 164),
        (37, 109, 64, 128),
        (37, 71, 64, 90),
        (104, 109, 131, 128),
    ),
}


@pytest.mark.parametrize("scale", (1, 2))
def test_mock_text_hi_at_every_anchor_240(panel, scale):
    for at, expected in zip(ANCHORS, HI_240[scale]):
        s, raw = panel()
        s.text("Hi", at=at, scale=scale)
        assert box(raw, WHITE) == expected, at
        assert not outside(raw), at


# Arduino kTitles[240]: the GRAY ink box of title(s). Every title sits on row 37
# (the cap 14 is above the floor 37) and is cut at the chord of its ink rows.
TITLES_240 = {
    "Distance": (88, 39, 150, 48),
    "Temperature": (76, 39, 162, 51),
    "Comfort": (92, 39, 146, 48),
    "Battery": (92, 39, 146, 51),
    "Mood": (104, 39, 134, 48),
    "ABCDEFGHIJKLM": (68, 39, 170, 48),
    "ABCDEFGHIJKLMNOPQRST": (40, 39, 199, 50),
    "_" * 14: (64, 51, 174, 51),
    "_" * 14 + "T": (60, 39, 179, 51),
    "Températureéééé": (60, 38, 178, 51),
    "ABCDEFGHIJKLMNOPQRSTUVW": (32, 39, 206, 50),
    "_" * 22: (32, 51, 206, 51),
}


@pytest.mark.parametrize("text", sorted(TITLES_240))
def test_mock_title_rows_and_cut_at_240(panel, text):
    s, raw = panel()
    s.title(text)
    assert box(raw, GRAY) == TITLES_240[text]
    assert set(lit(raw).values()) == {GRAY}


@pytest.mark.parametrize("size", (128, 240))
def test_mock_text_scale_0_counts_as_1(panel, size):
    # Arduino treats scale 0 as 1; at k > 1 it used to give f = 0 and draw nothing.
    # The pixel text (x, y) form too: on 240 it is Spleen 8x16 x scale.
    for at in ("N", "CENTER", "SW", (10, 20)):
        s, raw = panel(size)
        s.text("Hi", at=at, scale=0)
        zero = lit(raw)
        s, raw = panel(size)
        s.text("Hi", at=at, scale=1)
        assert zero, at
        assert zero == lit(raw), at


@pytest.mark.parametrize("size", (128, 240))
@pytest.mark.parametrize("scale", (1, 2, 3))
@pytest.mark.parametrize("text", ("MWM", "Été", "Hi"))
def test_mock_text_box_is_8_px_per_character_times_scale(panel, size, scale, text):
    # The README "Units and Scale" rule: n characters at a given scale take
    # n * 8 * scale px by text_height(scale), on both panels (8x8 x scale on
    # 128 px, Spleen 8x16 x scale on 240 px), at (x, y) and at a cardinal
    # position. The last cell starts (n - 1) * 8 * scale px after the first.
    n = len(text)
    w = n * 8 * scale
    s, raw = panel(size)
    h = s.text_height(scale)
    assert h == (8 if size == 128 else 16) * scale
    s.text(text, at=(10, 20), scale=scale)
    x0, y0, x1, y1 = box(raw)
    assert x0 >= 10 and x1 < 10 + w
    assert y0 >= 20 and y1 < 20 + h
    assert x1 >= 10 + (n - 1) * 8 * scale
    s, raw = panel(size)
    s.text(text, at="CENTER", scale=scale)
    x0, y0, x1, y1 = box(raw)
    assert (n - 1) * 8 * scale < x1 - x0 + 1 <= w
    assert y1 - y0 + 1 <= h


def test_mock_title_at_scale_2_sits_at_its_floor(panel):
    # Arduino test_title_rows: text("ABCDEFGH", N, WHITE, 2) on 240, 8x16 x 2, cell
    # (56, 67), the 8 cells kept.
    s, raw = panel()
    s.text("ABCDEFGH", at="N", scale=2)
    assert box(raw, WHITE) == (56, 71, 181, 90)


def test_mock_lowercase_title_takes_its_width_from_its_inked_rows(panel, mods):
    # Arduino test_title_band: a lowercase title inks rows 5..11 of its 8x16
    # cells (from row 42), and is cut at the chord of those rows: 22 cells.
    steami_screen, _ = mods
    s, raw = panel()
    s.title("acemnorsuvwxz")
    assert box(raw, GRAY) == (68, 42, 170, 48)
    t = "acemnorsuvwxzacemnorsuv"
    s, raw = panel()
    s.title(t)
    cut = lit(raw)
    s, raw = panel()
    s.text(t[:22], at=(32, 37), color=steami_screen.GRAY)
    assert cut == lit(raw)


class RecordingDisplay:
    """A 240 px display that records draw_scaled_text, draw_glyphs and text calls."""

    width = height = 240

    def __init__(self):
        self.calls = []

    def text(self, s, x, y, c):
        self.calls.append(("text", s, x, y, 1))

    def draw_scaled_text(self, s, x, y, c, scale):
        self.calls.append(("scaled", s, x, y, scale))

    def draw_glyphs(self, fc, glyphs, n, bold, c):
        self.calls.append(("glyphs", fc[0], fc[1], list(glyphs), n, bold))

    def fill(self, c):
        pass

    def pixel(self, x, y, c):
        pass

    def line(self, *a):
        pass

    def fill_rect(self, *a):
        pass

    def rect(self, *a):
        pass


def test_mock_long_title_draws_only_glyphs_inside_the_circle(panel, mods):
    # A 22-character title at 240 raises nothing: on row 37 the chord of its
    # ink rows (39..51) holds the 22 cells, drawn from x 32, all inside.
    steami_screen, _ = mods
    s, raw = panel()
    s.title("A very long title text")
    assert box(raw, GRAY) == (32, 39, 206, 51)
    assert not outside(raw, slack=0)
    title = lit(raw)
    s, raw = panel()
    s.text("A very long title text", at=(32, 37), color=steami_screen.GRAY)
    assert title == lit(raw)


@pytest.mark.parametrize(
    "text",
    ("A very long title text", "x" * 40, "Temperature extérieure", "_" * 30, "      x"),
)
def test_mock_long_texts_stay_inside_the_circle(panel, text):
    for at in ANCHORS:
        for scale in (1, 2, 3):
            s, raw = panel()
            s.text(text, at=at, scale=scale)
            # At scale 1 something always fits; "      x" keeps only its
            # blank prefix from scale 2 (the longest prefix that fits).
            assert lit(raw) or scale > 1, (at, scale)
            assert not outside(raw, slack=0), (at, scale)
    s, raw = panel()
    s.title(text)
    assert lit(raw)
    assert not outside(raw, slack=0)


def test_mock_widget_text_routes_to_the_spleen_faces(mods):
    steami_screen, _ = mods
    fonts = sys.modules["steami_screen.fonts"]
    d = RecordingDisplay()
    s = steami_screen.Screen(d)
    s.title("Hi")
    s.text("Hi", at="NE")
    s.text("Hi", at="S", scale=2)
    s.value(42)
    s.text("xy", at=(10, 20))  # real pixels: Spleen 8x16 x scale
    s.text("xy", at=(10, 20), scale=3)
    spleen = sys.modules["steami_screen.spleen"]
    f8x16 = spleen.F8X16
    o_h, o_i = fonts.offset(f8x16, "H"), fonts.offset(f8x16, "i")
    o_4, o_2 = fonts.offset(spleen.F16X32, "4"), fonts.offset(spleen.F16X32, "2")
    # Title and text(at=...) are 8x16 x f/2; value(42) is 16x32 at f 4, bold.
    assert d.calls[:4] == [
        ("glyphs", 8, 16, [(o_h, 112, 37), (o_i, 120, 37)], 1, 0),
        ("glyphs", 8, 16, [(o_h, 191, 37), (o_i, 199, 37)], 1, 0),
        ("glyphs", 8, 16, [(o_h, 104, 141), (o_i, 120, 141)], 2, 0),
        ("glyphs", 16, 32, [(o_4, 104, 104), (o_2, 120, 104)], 1, 1),
    ]
    o_x, o_y = fonts.offset(f8x16, "x"), fonts.offset(f8x16, "y")
    assert d.calls[4:] == [
        ("glyphs", 8, 16, [(o_x, 10, 20), (o_y, 18, 20)], 1, 0),
        ("glyphs", 8, 16, [(o_x, 10, 20), (o_y, 34, 20)], 3, 0),
    ]


# ----- subtitle -----

# Arduino kSubtitles[240]: the DARK ink box of each line (8x16 cells, one line on
# row 202 = S row 187 + u(8), two lines on rows 177 and 197).
SUBTITLES_240 = (
    (("VL53L1X ToF",), ((76, 204, 162, 213),)),
    (("WSEN-HIDS",), ((84, 204, 154, 213),)),
    (("SURPRISED",), ((84, 204, 154, 213),)),
    (("BME280",), ((96, 204, 142, 213),)),
    (("BQ27441",), ((92, 204, 146, 215),)),
    (("VL53L1X",), ((92, 204, 146, 213),)),
    (("Comfortable",), ((76, 204, 162, 213),)),
    (("Uncomfortable",), ((68, 204, 170, 213),)),
    (("20s window",), ((80, 204, 158, 213),)),
    (("3842 mV", "BQ27441"), ((92, 179, 146, 188), (92, 199, 146, 210))),
    (("Comfortable", "BME280"), ((76, 179, 162, 188), (96, 199, 142, 208))),
    (("Uncomfortable", "BME280"), ((68, 179, 170, 188), (96, 199, 142, 208))),
    (("Comfortable", "WSEN-HIDS"), ((76, 179, 162, 188), (84, 199, 154, 208))),
    (("WSEN-HIDS", "20s window"), ((84, 179, 154, 188), (80, 199, 158, 208))),
)


@pytest.mark.parametrize("lines,boxes", SUBTITLES_240)
def test_mock_subtitle_rises_until_its_lines_fit_at_240(panel, lines, boxes):
    s, raw = panel()
    s.subtitle(*lines)
    for b in boxes:
        assert box(raw, DARK, b[1], b[1] + 15) == b, lines
    assert not outside(raw, slack=0)


def test_mock_subtitle_cuts_a_line_that_cannot_fit(panel):
    s, raw = panel()
    s.subtitle("ABCDEFGHIJKLMNOPQRST", "x", "ABCDEFGHIJKLMNOPQRST")
    assert box(raw, DARK) is not None
    assert not outside(raw, slack=0)


# ----- value -----

# Value faces on 240 (design 5.1): f 2 is 8x16, f 3 12x24, f 4 16x32, judged on
# the whole text; '.' and ':' are narrow (half advance), 12x24 and 16x32 are
# bold. The fit lowers f from scale * k down to k and skips a factor without a
# face. Ink rows: 16x32 digits 6..25, 12x24 4..18, 8x16 2..11, 6x12 1..8.


def test_mock_value_center_with_unit_and_offset(panel):
    # Arduino kValues "72", "%", CENTER, yOffset -12: block 8f + 8f/3 + 8k = 58 at
    # f 4, top 120 + u(-12) - 29 = 69 (16x32 ink 75..94); the unit 8x16 at top + 8f.
    s, raw = panel()
    s.value(72, unit="%", y_offset=-12)
    assert box(raw, WHITE) == (106, 75, 134, 94)
    assert box(raw, LIGHT) == (117, 103, 122, 112)


def test_mock_value_center_default(panel):
    # Arduino: f = 2k = 4, no unit: top cy - 8f/2 = 104, 16x32 bold; "23.5" is
    # 16 + 16 + 8 + 16 = 56 px wide (narrow '.').
    s, raw = panel()
    s.value(23.5)
    assert box(raw, WHITE) == (94, 110, 146, 129)
    s, raw = panel()
    s.value(8)
    assert box(raw, WHITE) == (114, 110, 126, 129)
    assert count(raw, WHITE) == 146


def test_mock_value_program_04_and_01(panel):
    # Arduino programs 04 (distance) and 01 (temperature): value and unit.
    s, raw = panel()
    s.value(342, unit="mm")
    assert box(raw, WHITE) == (98, 97, 142, 116)
    assert box(raw, LIGHT) == (112, 128, 126, 134)
    s, raw = panel()
    s.value(23.5, unit="°C")
    assert box(raw, WHITE) == (94, 97, 146, 116)
    assert box(raw, LIGHT) == (113, 124, 126, 134)


def test_mock_value_at_n_and_s(panel):
    # Arduino: at N the 16x32 value sits on the floor row 67 of f 4, the unit
    # 8x16 at 67 + 8f = 99; S mirrors it.
    s, raw = panel()
    s.value(23.5, unit="°C", at="N")
    assert box(raw, WHITE) == (94, 73, 146, 92)
    assert box(raw, LIGHT) == (113, 100, 126, 110)
    s, raw = panel()
    s.value(23.5, unit="°C", at="S")
    assert box(raw, WHITE) == (94, 147, 146, 166)
    assert box(raw, LIGHT) == (113, 174, 126, 184)


# Arduino kSides[240]: value(text, "C", W or E). The half region is sized for
# the widest of the text and "88.8" (14f with the narrow '.').
SIDES_240 = {
    "1": ((55, 97, 65, 116), (175, 97, 185, 116)),
    "8888": ((30, 97, 90, 116), (150, 97, 210, 116)),
    "123456": ((15, 97, 106, 116), (135, 97, 226, 116)),
    "12:34:56": ((20, 100, 101, 114), (141, 100, 222, 114)),
}


@pytest.mark.parametrize("text", sorted(SIDES_240))
def test_mock_value_side_by_side(panel, text):
    for at, expected in zip(("W", "E"), SIDES_240[text]):
        s, raw = panel()
        s.value(text, unit="C", at=at)
        assert box(raw, WHITE) == expected, at


def test_mock_value_mockup_03(panel):
    # Arduino mockup 03: two values side by side, with label and unit.
    s, raw = panel()
    s.value(23.5, "°C", "W", "TEMP")
    assert box(raw, WHITE) == (34, 97, 86, 116)
    assert box(raw, GRAY) == (51, 73, 73, 80)
    assert box(raw, LIGHT) == (52, 124, 65, 134)
    s, raw = panel()
    s.value(45.3, "%", "E", "HUM")
    assert box(raw, WHITE) == (154, 97, 206, 116)
    assert box(raw, GRAY) == (168, 73, 184, 80)
    assert box(raw, LIGHT) == (179, 125, 184, 134)


def test_mock_value_side_is_cut_at_factor_k(panel):
    # Arduino test_value_truncation: at the floor f = k = 2 (8x16, TEXT ladder),
    # "Uncomfortable" and "ABCDEFGHIJKLMNO" are cut to the same 13 cells.
    for text in ("Uncomfortable", "ABCDEFGHIJKLMNO"):
        s, raw = panel()
        s.value(text, unit="C", at="W")
        assert box(raw, WHITE) == (7, 104, 109, 113), text


def test_mock_value_center_cut_near_the_edge(panel):
    # Arduino test_value_truncation: 15 '8' with a unit at yOffset -50 fall to
    # f 2 and are cut at the chord of their ink rows.
    s, raw = panel()
    s.value("888888888888888", unit="C", y_offset=-50)
    assert box(raw, WHITE) == (76, 11, 162, 20)


def test_mock_value_label_and_unit_stay_in_their_half(panel):
    # rule: label 6x12 at top - u(4) - 12; at W the label and unit are cut to
    # [chord left + k, cx - u(3) - 1] at their own rows and centred there.
    for at in ("W", "E"):
        s, raw = panel()
        s.value(23, unit="ABCDEFGHIJ", at=at, label="TEMPERATURE")
        label, unit = box(raw, GRAY), box(raw, LIGHT)
        assert label and unit
        if at == "W":
            assert label[2] <= 114 and unit[2] <= 114
        else:
            assert label[0] >= 126 and unit[0] >= 126
        assert not outside(raw, slack=0)


@pytest.mark.parametrize("at", ANCHORS)
def test_mock_value_stays_inside_at_every_anchor(panel, at):
    for text in ("8", "23.5", "-1234.56", "Uncomfortable"):
        s, raw = panel()
        s.value(text, unit="kPa", at=at, label="Pressure")
        assert box(raw, WHITE), (at, text)
        assert not outside(raw, slack=0), (at, text)


def test_mock_value_floor_is_k_at_the_corners(panel):
    # Design 5.1: f never falls below k, corners included. At NE scale 1 the
    # value is 8x16 on row 37 (ink 39..48), its label 6x12 at 37 - 7 - 12 = 18
    # (ink 19..26), the unit at 37 + 8f = 53.
    s, raw = panel()
    s.value(8, "C", "NE", "TEMP", scale=1)
    assert box(raw, WHITE) == (197, 39, 203, 48)
    assert box(raw, GRAY) == (159, 19, 181, 26)
    assert box(raw, LIGHT) == (197, 55, 203, 64)
    assert not outside(raw, slack=0)
    s, raw = panel()
    s.value(8, "C", "NW", "TEMP", scale=1)
    label, value = box(raw, GRAY), box(raw, WHITE)
    assert label and value
    assert label[3] < value[1]
    assert not outside(raw, slack=0)
    s, raw = panel()
    s.value("Temperature", at="N", label="X", scale=1)
    assert box(raw, WHITE)[1] == 39
    assert box(raw, GRAY)[3] < 37
    assert not outside(raw, slack=0)


def test_mock_value_label_row_unchanged_when_it_fits(panel):
    # Arduino: the label cell top stays at value top - u(4) - 12 when it fits
    # (16x32 value top 67 at f 4, label cell 48, ink 49..56).
    s, raw = panel()
    s.value(8, "C", "NE", "TEMP")
    assert box(raw, GRAY) == (183, 49, 205, 56)
    assert box(raw, WHITE) == (189, 73, 201, 92)
    assert box(raw, LIGHT) == (191, 101, 197, 110)


def test_mock_value_fit_floor_and_skipped_factors(panel):
    # Arduino: from scale 4 (f 8) the fit falls to f 2 for wide texts; at W
    # "8888" skips f 7 (no face) and takes f 6, 12x24 x 2 (ink 104..133).
    s, raw = panel()
    s.value("888888888888888", "°C", y_offset=-50, scale=4)
    assert box(raw, WHITE) == (76, 11, 162, 20)
    s, raw = panel()
    s.value("ABCDEFGHIJKLMNO", at="W", scale=4)
    assert box(raw, WHITE) == (3, 114, 113, 123)
    s, raw = panel()
    s.value("ABCDEFGHIJKLMNO", at="NE", scale=4)
    assert box(raw, WHITE) == (85, 39, 203, 48)
    s, raw = panel()
    s.value(8888, at="W", scale=4)
    assert box(raw, WHITE) == (14, 104, 107, 133)


def test_mock_value_bold_stays_in_its_cells(panel):
    # Design 5.2: the bold strike at x + n stays inside the cells (16x32 at
    # f 4: 4 * 16 + 8 = 72 px from x 84; 12x24 x 2 at f 6: 4 * 24 + 12 = 108 px
    # from x 66).
    s, raw = panel()
    s.value("-88.8")
    assert count(raw, WHITE) == 473
    assert all(84 <= x < 156 for (x, _), c in lit(raw).items() if c == WHITE)
    s, raw = panel()
    s.value("-88.8", scale=3)
    assert count(raw, WHITE) == 1176
    assert all(66 <= x < 174 for (x, _), c in lit(raw).items() if c == WHITE)


def test_mock_value_narrow_colon(panel):
    # Design 5.2: "12:30 PM" takes the TEXT ladder (8x16 at f 2) and keeps the
    # narrow ':' of the VALUE ink: its pen is at 106 and it is drawn 2 px left,
    # so its ink (8x16 columns 3..4) lands on columns 107..108.
    s, raw = panel()
    s.value("12:30 PM", scale=1)
    assert box(raw, WHITE) == (91, 114, 148, 123)
    assert count(raw, WHITE) == 228
    colon = [p for p, c in lit(raw).items() if c == WHITE and 106 <= p[0] <= 109]
    assert colon
    assert {x for x, _ in colon} <= {107, 108}
    assert all(117 <= y <= 123 for _, y in colon)


def test_mock_value_unknown_character(panel):
    # Review Focus 2: '€' is a '?' cell, and the text takes the TEXT ladder.
    s, raw = panel()
    s.value("€5")
    euro = lit(raw)
    s, raw = panel()
    s.value("?5")
    assert euro == lit(raw)
    assert box(raw, WHITE) == (104, 108, 133, 127)
    assert count(raw, WHITE) == 236


def test_mock_value_face_follows_the_whole_text(mods):
    # Review Focus 5: str(val) forms that are not plain numbers take the TEXT
    # ladder (8x16 x 2 at f 4, never bold); "-0.5" takes the value set.
    steami_screen, _ = mods
    d = RecordingDisplay()
    s = steami_screen.Screen(d)
    for val, expected in (
        (float("nan"), (8, 16, 3, 2, 0)),
        (1e-05, (8, 16, 5, 2, 0)),
        (-0.5, (16, 32, 4, 1, 1)),
    ):
        s.value(val)
        kind, w, h, glyphs, n, bold = d.calls[-1]
        assert kind == "glyphs"
        assert (w, h, len(glyphs), n, bold) == expected, val


def test_mock_value_of_empty_text_raises_nothing(panel):
    # Review Focus 4.
    s, raw = panel()
    s.value("")
    assert count(raw, WHITE) == 0
    s, raw = panel()
    s.value("", unit="", label="")
    s.value(" ")
    assert not outside(raw, slack=0)


def test_mock_value_label_never_enters_the_value_rows(panel):
    # Kept MicroPython difference: a label of which no character fits is
    # lowered (never into the value's rows), not dropped. At y_offset -40 the
    # value top is 16 and the label cell row 16 - 7 - 12 = -3, whose ink rows
    # leave the circle.
    for y_offset in range(-64, -39, 4):
        s, raw = panel()
        s.value(8, "C", label="TEMP", y_offset=y_offset)
        label, value = box(raw, GRAY), box(raw, WHITE)
        if label and value:
            assert label[3] < value[1], y_offset
        assert not outside(raw, slack=0), y_offset
        if y_offset == -40:
            assert label is not None


# ----- bar, gauge -----


def test_mock_bar_at_240(panel):
    # Arduino test_bar_golden: W - u(40) = 165 wide from x 38, u(8) = 15 rows from
    # cy + u(20) + u(-12) = 135; fill int(165 * 72 / 100) = 118 columns. The
    # track is GRID_DARK, as in Arduino (#437).
    s, raw = panel()
    s.bar(72, 100, -12, color=(119, 255, 119))
    assert box(raw, GREEN) == (38, 135, 155, 149)
    assert count(raw, GREEN) == 118 * 15
    assert box(raw, GRID_DARK) == (156, 135, 202, 149)
    assert count(raw, GRID_DARK) == 47 * 15


@pytest.mark.parametrize("y_offset", (0, 12, 25, 40, 60, -80))
@pytest.mark.parametrize("size", (240, 128))
def test_mock_bar_is_clipped_to_the_circle_per_row(panel, size, y_offset):
    # Arduino rule 7 and barRows(): each row of the track and of the fill is
    # cut to the chord of that row, so a bar far from the centre stays inside
    # the circle (#456). 240, y_offset 25: rows 203..217, the bottom row's
    # chord 50..190 against the bar's 38..202. y_offset 60 is below the panel
    # on 240 (top 269): nothing is drawn. 0 and 12 fit whole (one rect).
    s, raw = panel(size)
    s.bar(50, y_offset=y_offset, color=(119, 255, 119))
    w = size - s.u(40)
    x = size // 2 - w // 2
    top = size // 2 + s.u(20) + s.u(y_offset)
    fill = w // 2
    expected = {}
    for y in range(max(top, 0), min(top + s.u(8), size)):
        c = s._chord(y, y)
        if c is None:
            continue
        for px in range(max(x, c[0]), min(x + w - 1, c[1], size - 1) + 1):
            expected[(px, y)] = GREEN if px < x + fill else GRID_DARK
    assert lit(raw) == expected
    assert not outside(raw, slack=0)
    if y_offset in (25, 40):
        assert expected, "the bar is still drawn where the circle leaves room"


def test_mock_gauge_ring_at_240(panel):
    # Arduino test_gauge_ring: outer radius radius - u(4) = 113, thickness
    # max(5, radius // 9) = 13: rows 7..19 at the top of the centre column.
    s, raw = panel()
    s.gauge(0)
    px = lit(raw)
    assert [y for y in range(40) if px.get((120, y)) == DARK] == list(range(7, 20))
    # Arduino kGaugeLabels: 6x12 labels, their cell top 169 at distance
    # outer - 13 - u(10) = 82, angle 233 (min) and 127 (max); "0" centred on
    # x 55 (cell 52), "100" on x 185 (cell 176), ink rows 170..177.
    assert box(raw, GRAY) == (52, 170, 192, 177)
    assert not outside(raw, slack=0)


def test_mock_gauge_arc_width_is_in_real_pixels(panel):
    s, raw = panel()
    s.gauge(0, arc_width=6)
    px = lit(raw)
    # outer 113, centre radius 113 - 3 = 110: rows 7..13 (dr -3..3).
    assert [y for y in range(40) if px.get((120, y)) == DARK] == list(range(7, 14))


def arc_errors(raw, r, width, start, sweep, margin=1.0):
    """(holes, strays) of an arc drawn on a black frame around the panel centre.

    The ring is the Arduino one: 4 d^2 between (2 ri - 1)^2 and (2 ro + 1)^2,
    ro = r + width // 2, ri = r - width // 2; the sector is start .. start +
    sweep, clockwise. Pixels within `margin` px of a sector edge are not
    judged. holes: unlit ring pixels inside the sector; strays: lit pixels
    outside the ring or the sector.
    """
    c = raw.width // 2
    half = width // 2
    o2, i2 = (2 * (r + half) + 1) ** 2, (2 * max(0, r - half) - 1) ** 2
    px = lit(raw)
    holes, strays = [], []
    for y in range(raw.height):
        for x in range(raw.width):
            dx, dy = x - c, y - c
            on = (x, y) in px
            if not i2 <= 4 * (dx * dx + dy * dy) <= o2:
                if on:
                    strays.append((x, y))
                continue
            rel = (math.degrees(math.atan2(dy, dx)) - start) % 360
            inside = sweep >= 360 or rel <= sweep
            edge = 0 if sweep >= 360 else min(rel, abs(rel - sweep), 360 - rel)
            if math.hypot(dx, dy) * math.radians(edge) < margin:
                continue
            if inside and not on:
                holes.append((x, y))
            elif on and not inside:
                strays.append((x, y))
    return holes, strays


@pytest.mark.parametrize("size", (128, 240))
@pytest.mark.parametrize("sweep", (1, 90, 135, 180, 181, 200, 270, 359, 360))
def test_mock_arc_is_a_solid_ring_sector(panel, size, sweep):
    # Arduino 5.6 arc(): every ring pixel inside the sector is lit (no pinholes),
    # none outside it; the end stops at start + sweep, clockwise from 135.
    for r, width in ((size // 2 - 8, 7), (size // 2 - 20, 31)):
        s, raw = panel(size)
        s._draw_arc(size // 2, size // 2, r, 135, sweep, (255, 255, 255), width)
        holes, strays = arc_errors(raw, r, width, 135, sweep)
        assert not holes, (r, width, holes[:5])
        assert not strays, (r, width, strays[:5])
        assert set(lit(raw).values()) == {WHITE}


@pytest.mark.parametrize("size", (128, 240))
def test_mock_arc_end_angles(panel, size):
    # A pixel on the ring just past either end (2 degrees) is unset, one just
    # inside is set: start 135 (lower left), sweeps < 180 and > 180.
    c = size // 2
    r = c - 10
    for sweep in (90, 200, 270):
        s, raw = panel(size)
        s._draw_arc(c, c, r, 135, sweep, (255, 255, 255), 5)
        px = lit(raw)
        for deg, on in ((133, False), (137, True), (135 + sweep - 2, True), (137 + sweep, False)):
            a = math.radians(deg)
            p = (round(c + r * math.cos(a)), round(c + r * math.sin(a)))
            assert (p in px) is on, (sweep, deg)


@pytest.mark.parametrize("size", (128, 240))
def test_mock_arc_sweep_0_draws_nothing(panel, size):
    s, raw = panel(size)
    s._draw_arc(size // 2, size // 2, size // 3, 135, 0, (255, 255, 255), 9)
    assert not lit(raw)


@pytest.mark.parametrize("size", (128, 240))
def test_mock_gauge_arcs_are_solid(panel, size):
    # The full gauge: track and fill are solid rings (the old point-by-point
    # arc left single-pixel holes in thick arcs).
    s, raw = panel(size)
    w = s.u(17)
    s.gauge(100, arc_width=w, color=(255, 255, 255))
    r = s.radius - w // 2 - (1 if s.k == 1 else s.u(4))
    holes, _ = arc_errors(raw, r, w + 2, 135, 270)
    assert not holes, holes[:5]


def test_mock_arc_uses_the_adapter_draw_arc(panel):
    s, raw = panel()
    calls = []
    s._d.draw_arc = lambda *a: calls.append(a)
    s.gauge(50)
    assert calls == [
        (120, 120, 107, 135, 270, (102, 102, 102), 13),
        (120, 120, 107, 135, 135, (187, 187, 187), 15),
    ]
    assert count(raw, DARK) == 0
    assert count(raw, LIGHT) == 0


# ----- face, watch, compass -----


@pytest.mark.parametrize(
    "compact,cell,ox,oy",
    ((False, 20, 40, 40), (True, 15, 60, 53)),  # Arduino faceGrid(240)
)
def test_mock_face_grid_at_240(panel, mods, compact, cell, ox, oy):
    steami_screen, _ = mods
    s, raw = panel()
    s.face("happy", compact=compact)
    bitmap = steami_screen.FACES["happy"]
    expected = {
        (ox + c * cell + dx, oy + r * cell + dy)
        for r in range(8)
        for c in range(8)
        if bitmap[r] & (0x80 >> c)
        for dx in range(cell)
        for dy in range(cell)
    }
    assert set(lit(raw)) == expected


def test_mock_watch_numbers_at_240(panel):
    # Arduino test_watch_numbers_golden: "12", "3", "6", "9" at R - u(15) = 77,
    # 8x16 cells centred on their points (x - tw // 2, y - text_height() // 2).
    s, raw = panel()
    s.watch(1, 37, 5)
    assert box(raw, WHITE) == (39, 37, 199, 200)
    assert not outside(raw, slack=0)


def test_mock_watch_hands_at_240(panel):
    # Arduino test_watch_hands_at_three and test_watch_integer_angles (10:10:30,
    # where the MicroPython float angles equal the Arduino integer ones).
    s, raw = panel()
    s.watch(3, 0, 0, color=(255, 85, 85))
    px = lit(raw)
    assert px[(172, 120)] == RED
    assert box(raw, RED)[2] == 172
    assert px[(120, 42)] == GRAY  # minute tip under the second hand
    assert px[(120, 31)] == GRAY  # second tip
    assert px[(120, 120)] == GRAY  # pivot
    s, raw = panel()
    s.watch(10, 10, 30)
    px = lit(raw)
    assert px[(77, 90)] == LIGHT
    assert px[(189, 85)] == LIGHT
    assert px[(120, 209)] == GRAY


def test_mock_circles_are_k_wide_strokes(panel):
    # rule: the compass inner circle int(R * 0.7) = 68 (R = 120 - u(12) = 98) is a
    # ring k = 2 px wide, radii 67 and 68: rows 52 and 53 of the centre column
    # (the needle at 90 leaves that column free).
    s, raw = panel()
    s.compass(90)
    px = lit(raw)
    assert [y for y in range(40, 100) if px.get((120, y)) == DARK] == [52, 53]


@pytest.mark.parametrize(
    "heading,tip",
    # Arduino kCompassCases at 0 and 180 (the MicroPython rose does not turn);
    # rule at 90 and 270: needle R * 0.85 = 83 toward the heading, R = 120 - u(12).
    ((0, (120, 37)), (180, (120, 203)), (90, (203, 120)), (270, (37, 120))),
)
def test_mock_compass_at_240(panel, heading, tip):
    s, raw = panel()
    s.compass(heading, color=(255, 85, 85))
    px = lit(raw)
    assert px[tip] == RED
    assert px[(120, 120)] == GRAY
    # Arduino kCompassCases at heading 0: the N 8x16 cell centred at R + u(5) =
    # 107 above the centre, cell (116, 5); the MicroPython rose does not turn,
    # so the N box is the same at every heading.
    assert box(raw, WHITE) == (116, 7, 122, 16)
    assert not outside(raw, slack=0)


# ----- menu, graph -----


def test_mock_menu_shows_five_rows_inside_the_circle(panel):
    # Arduino section 5.9 menu: rows u(35 + 14 j), a row is used when the chord at
    # its cell rows holds 12 cells (192 px): 5 rows on 240 (MicroPython: 6 on 128).
    # Kept MicroPython difference: Arduino shows 6 rows with a bar clipped per
    # scanline; the items are 8x16 text.
    items = ["Temperature", "Humidity", "Pressure", "Light", "Sound", "Distance", "Battery"]
    s, raw = panel()
    s.menu(items, selected=0)
    tops = [65, 91, 118, 144, 170]
    rows = sorted({y for (x, y), c in lit(raw).items() if c in (WHITE, GRAY)})
    assert rows[0] >= tops[0] and rows[-1] <= tops[-1] + 15
    for top in tops:
        assert box(raw, None, top, top + 15) is not None
    # The selected bar: x u(15) = 28, width W - u(30) = 184, from row 65 - u(2) = 62,
    # u(14) = 26 rows.
    assert box(raw, DARK) == (28, 62, 211, 87)
    assert not outside(raw, slack=0)


def test_mock_menu_cuts_long_items(panel):
    s, raw = panel()
    s.menu(["A very long menu item", "x" * 30, "ok"], selected=1)
    assert box(raw, WHITE) is not None
    assert not outside(raw, slack=0)


def test_mock_graph_box_at_240(panel):
    # Arduino section 5.9 graph box: x u(21) = 39, y u(38) = 71, w W - u(15) - u(21)
    # = 173, h u(52) = 97; axes DARK with a k = 2 stroke (a 2 x 2 brush, so the
    # bottom axis from x 39 to 211 reaches 212).
    s, raw = panel()
    s.graph([], min_val=0, max_val=100)
    px = lit(raw)
    assert px[(39, 71)] == DARK and px[(40, 71)] == DARK
    assert px.get((38, 71)) is None and px.get((41, 100)) is None
    assert px[(39, 168)] == DARK and px[(212, 168)] == DARK and px[(212, 169)] == DARK
    assert px.get((213, 168)) is None and px.get((100, 170)) is None
    assert not outside(raw, slack=0)


def test_mock_graph_value_and_labels_at_240(panel):
    s, raw = panel()
    s.graph([10, 30, 20, 70, 55, 90], color=(119, 255, 119))
    # rule: value "90" 8x16 (TEXT at k) centred on cx at row u(31) = 58, digits
    # ink rows 2..11.
    assert box(raw, WHITE) == (112, 60, 126, 69)
    # rule: the labels sit inside the box (right of the axis), not left of it.
    labels = [p for p, c in lit(raw).items() if c == DARK and p[0] > 41 and p[1] < 168]
    assert labels and min(p[0] for p in labels) >= 39 + 2 + 3
    assert box(raw, GREEN) is not None
    assert not outside(raw, slack=0)


@pytest.mark.parametrize("max_val", (100, 2000))
def test_mock_graph_labels_clear_the_axes_at_240(panel, max_val):
    # Arduino 5.9: the labels sit inside the box, clear of its lines. Box rows
    # u(38) = 71 .. 71 + u(52) = 168; bottom axis rows 168-169 (k = 2), dashed
    # mid line row 71 + 48 = 119. Max label first ink row 71 + u(2) = 74; the
    # mid and min labels' last ink row k + u(2) = 5 above their line: 114 and
    # 163. The 6x12 digits and "k" ink rows 1..8: 8 rows per label.
    # Kept MicroPython difference: three labels ("100", "50", "0" or "2k",
    # "1k", "0"), where Arduino draws its own set.
    s, raw = panel()
    s.graph([], min_val=0, max_val=max_val)
    rows = sorted({y for (x, y), c in lit(raw).items() if c == DARK and x >= 44 and y < 168})
    bands = [(74, 81), (107, 114), (156, 163)]
    assert rows == [y for a, b in bands for y in range(a, b + 1)]
    assert not {119, 168, 169} & set(rows)
    px = lit(raw)
    # The dashes and the axis cross no label: rows 119 and 168 keep their own
    # colour only, and no label pixel touches the row next to them.
    assert {px[(x, 119)] for x in range(41, 76) if (x, 119) in px} == {GRID_DARK}
    assert not [y for y in rows if y in (118, 120, 167)]


# int(1e30) and int(-1e38) are 31 and 39 digits: wider than the chord.
LONG_GRAPHS = (
    ([0, 123456789], 0, 100),
    ([0, -1e9], 0, 100),
    ([1, 2], -99999, 99999),
    ([1, 2], -123456789, 123456789),
    ([0, 1e30], 0, 100),
    ([0, -1e38], 0, 100),
    ([1, 2], -1e30, 1e30),
    ([1, 2], -1e38, 1e38),
)


@pytest.mark.parametrize(("data", "lo", "hi"), LONG_GRAPHS)
def test_mock_graph_fits_long_numbers_to_the_circle_at_240(panel, data, lo, hi):
    # Rule 7 (#456): the current value and the axis labels keep the longest
    # prefix that fits the chord at their ink rows. The value stays centred
    # on cx when it fits and is clamped into the chord when cut; the labels
    # keep their left edge (Arduino drawGraphLabel(): the room runs to the
    # chord's right edge less k).
    s, raw = panel()
    s.graph(data, lo, hi, color=(119, 255, 119))
    assert not outside(raw, slack=0)
    # The value's digits, ink rows 60..69 (cell 58, rows 2..11): chord 17..223.
    white = box(raw, WHITE)
    assert white is not None and white[1] == 60 and white[3] <= 69
    assert white[0] >= 17 and white[2] <= 223
    text = str(int(data[-1]))
    if len(text) * 8 > 207:
        # Cut to 25 cells (200 px), not to nothing.
        assert white[2] - white[0] >= 24 * 8
    else:
        # Centred: the ink lies in the cells from 120 - width // 2.
        cell = 120 - len(text) * 4
        assert cell <= white[0] and white[2] < cell + len(text) * 8
    # The three labels keep their bands and their left edge, x 44.
    rows = sorted({y for (x, y), c in lit(raw).items() if c == DARK and x >= 44 and y < 168})
    bands = [(74, 81), (107, 114), (156, 163)]
    assert set(rows) <= {y for a, b in bands for y in range(a, b + 1)}
    for a, b in bands:
        xs = [x for (x, y), c in lit(raw).items() if c == DARK and x >= 42 and a <= y <= b]
        # The first ink column lies in the first 6 px cell, which starts at 44.
        assert xs and min(xs) < 44 + 6, (a, b)


NAN = float("nan")
# "--" in the current-value place (#463, Arduino 5.9: "-- if NAN", "0 or 1
# point draws the frame and the value only"): the 16 px wide text centred on
# cx at row u(31), as a two-digit value. 240: Spleen 8x16 (TEXT at k = 2),
# cell x 112..127, rows 58..73, the '-' ink is row 7 of the cell, columns
# 1..6 of each glyph. 128: the 8x8 framebuf path, cell x 56..71 from row 31.
DASHES = {240: (113, 65, 126, 65), 128: (57, 34, 70, 34)}
# Box left x, step base and width: x u(21) + 0, w W - u(15) - u(21).
GRAPH_X = {240: (39, 173), 128: (21, 92)}
# On 128 the three 8x8 axis labels sit left of the axis and are clipped by
# the circle (kept MicroPython difference), so only 240 checks the circle.


@pytest.mark.parametrize("size", (240, 128))
def test_mock_graph_empty_history_shows_dashes(panel, size):
    s, raw = panel(size)
    s.graph([], min_val=0, max_val=100, color=(119, 255, 119))
    assert box(raw, WHITE) == DASHES[size]
    gx, _gw = GRAPH_X[size]
    # The frame: the left axis at the box's left column, DARK.
    assert lit(raw)[(gx, s.u(38))] == DARK
    # No line.
    assert box(raw, GREEN) is None
    if size == 240:
        assert not outside(raw, slack=0)


@pytest.mark.parametrize("size", (240, 128))
def test_mock_graph_nan_last_value_shows_dashes(panel, size):
    s, raw = panel(size)
    s.graph([10, 30, NAN], color=(119, 255, 119))
    assert box(raw, WHITE) == DASHES[size]
    # The line joins the two numbers, from the box's left edge to the middle
    # point: the NaN point at the right edge has no segment.
    gx, gw = GRAPH_X[size]
    green = box(raw, GREEN)
    assert green is not None
    assert green[0] == gx and green[2] <= gx + gw // 2 + s.k
    if size == 240:
        assert not outside(raw, slack=0)


@pytest.mark.parametrize("last", (float("inf"), float("-inf")))
@pytest.mark.parametrize("size", (240, 128))
def test_mock_graph_infinite_last_value_shows_dashes(panel, size, last):
    # int(inf) raises OverflowError: an infinite last value shows "--" too.
    s, raw = panel(size)
    s.graph([10, 30, last], color=(119, 255, 119))
    assert box(raw, WHITE) == DASHES[size]
    assert box(raw, GREEN) is not None
    if size == 240:
        assert not outside(raw, slack=0)


@pytest.mark.parametrize("size", (240, 128))
def test_mock_graph_all_nan_shows_dashes_and_no_line(panel, size):
    s, raw = panel(size)
    s.graph([NAN, NAN, NAN], color=(119, 255, 119))
    assert box(raw, WHITE) == DASHES[size]
    assert box(raw, GREEN) is None


@pytest.mark.parametrize("size", (240, 128))
def test_mock_graph_skips_a_nan_point_in_the_middle(panel, size):
    # A NaN point is skipped and leaves a gap (Arduino 5.9: "NAN points are
    # skipped (gap in the curve)"): no segment reaches it, the points keep
    # their x, and the value is the last number.
    s, raw = panel(size)
    s.graph([10, NAN, 30, 70], color=(119, 255, 119))
    gx, gw = GRAPH_X[size]
    x2 = int(gx + 2 * gw / 3)
    green = box(raw, GREEN)
    assert green is not None
    # Only the segment from point 2 to point 3 is drawn.
    assert green[0] == x2 and green[2] >= gx + gw - 1
    ref, ref_raw = panel(size)
    ref.graph([10, 70])
    assert box(raw, WHITE) == box(ref_raw, WHITE)
    if size == 240:
        assert not outside(raw, slack=0)


@pytest.mark.parametrize("size", (240, 128))
def test_mock_graph_one_point_draws_the_frame_and_its_value(panel, size):
    s, raw = panel(size)
    s.graph([5], min_val=0, max_val=10, color=(119, 255, 119))
    white = box(raw, WHITE)
    assert white is not None and white != DASHES[size]
    # The frame: the left axis at the box's left column, DARK.
    gx, _gw = GRAPH_X[size]
    assert lit(raw)[(gx, s.u(38))] == DARK
    # The value "5", in the same place as a reference ending on 5.
    ref, ref_raw = panel(size)
    ref.graph([0, 5], min_val=0, max_val=10)
    assert white == box(ref_raw, WHITE)
    assert box(raw, GREEN) is None


# ----- everything stays inside at default arguments -----


def test_mock_default_widgets_stay_inside_the_circle(panel):
    calls = (
        lambda s: s.title("Hello"),
        lambda s: s.subtitle("one line"),
        lambda s: s.value(23.5, unit="C", label="Temp"),
        lambda s: s.bar(50),
        lambda s: s.bar(100, y_offset=12),
        lambda s: s.gauge(75),
        lambda s: s.graph([0, 100, 50, 25]),
        lambda s: s.menu(["a", "b", "c", "d", "e", "f", "g", "h"], selected=4),
        lambda s: s.compass(33),
        lambda s: s.watch(10, 8, 42),
        lambda s: s.face("love"),
    )
    for call in calls:
        s, raw = panel()
        call(s)
        assert lit(raw), call
        assert not outside(raw, slack=0), call


def test_mock_empty_texts_raise_nothing(panel):
    # Review Focus 4: empty and blank strings raise nothing and draw nothing
    # outside the circle.
    calls = (
        lambda s: s.title(""),
        lambda s: s.subtitle("", "x"),
        lambda s: s.subtitle(""),
        lambda s: s.menu([""]),
        lambda s: s.text("", at="N"),
        lambda s: s.text("   ", at="CENTER", scale=2),
        lambda s: s.graph([5], 0, 10),
    )
    for call in calls:
        s, raw = panel()
        call(s)
        assert not outside(raw, slack=0), call


def test_mock_radius_and_isqrt_never_fail(panel):
    s, _raw = panel()
    for y in (-500, -1, 0, 119, 120, 239, 240, 500):
        s._chord(y, y)
    assert s._chord(-1, 0) is None
    assert s._chord(41, 41) == (30, 210)
    assert s._chord(1, 14) == (105, 135)
    assert s._chord(63, 63)[1] - s._chord(63, 63)[0] + 1 == 211
    assert math.isclose(s.u(64), 120)
