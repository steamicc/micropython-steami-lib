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
    assert (s128.max_chars, s240.max_chars) == (16, 15)
    assert (s240.width, s240.height, s240.center, s240.radius) == (240, 240, (120, 120), 120)


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
    # Arduino test_scale_quantities: marginNs(tw, f) is the N row.
    for tw, f, row in ((16, 2, 37), (176, 2, 41), (208, 2, 63), (16, 4, 67), (16, 3, 52)):
        assert s._at("N", tw, f)[1] == row, (tw, f)
    # marginEw(2) 22 and marginEw(3) 30 are the W column.
    assert (s._at("W", 0, 2)[0], s._at("W", 0, 3)[0]) == (22, 30)


# ----- text(at=...), title -----

# Arduino kHiBoxes[240]: text("Hi", at, WHITE, scale) ink boxes, scale 1 then 2.
HI_240 = {
    1: (
        (106, 37, 129, 50),
        (175, 37, 198, 50),
        (188, 112, 211, 125),
        (178, 187, 201, 200),
        (106, 187, 129, 200),
        (35, 187, 58, 200),
        (24, 112, 47, 125),
        (38, 37, 61, 50),
        (106, 112, 129, 125),
    ),
    2: (
        (92, 67, 139, 94),
        (143, 67, 190, 94),
        (143, 105, 190, 132),
        (143, 141, 190, 168),
        (92, 141, 139, 168),
        (41, 141, 88, 168),
        (41, 105, 88, 132),
        (41, 67, 88, 94),
        (92, 105, 139, 132),
    ),
}


@pytest.mark.parametrize("scale", (1, 2))
def test_mock_text_hi_at_every_anchor_240(panel, scale):
    for at, expected in zip(ANCHORS, HI_240[scale]):
        s, raw = panel()
        s.text("Hi", at=at, scale=scale)
        assert box(raw, WHITE) == expected, at
        assert not outside(raw), at


# Arduino kTitles[240]: the GRAY ink box of title(s).
TITLES_240 = {
    "Temperature": (34, 41, 205, 56),
    "Comfort": (66, 37, 173, 50),
    "Battery": (66, 37, 173, 52),
    "ABCDEFGHIJKLM": (18, 63, 223, 76),
    "ABCDEFGHIJKLMNOPQRST": (18, 63, 223, 76),
    "______________": (16, 75, 223, 78),
    "______________T": (16, 75, 223, 78),
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
    for at in ("N", "CENTER", "SW"):
        s, raw = panel(size)
        s.text("Hi", at=at, scale=0)
        zero = lit(raw)
        s, raw = panel(size)
        s.text("Hi", at=at, scale=1)
        assert zero, at
        assert zero == lit(raw), at


def test_mock_title_at_scale_2_sits_at_its_floor(panel):
    # Arduino test_title_rows: text("ABCDEFGH", N, WHITE, 2) on 240, 6 cells kept at row 67.
    s, raw = panel()
    s.text("ABCDEFGH", at="N", scale=2)
    assert box(raw, WHITE) == (28, 67, 211, 94)


def test_mock_lowercase_title_takes_its_width_from_its_inked_rows(panel):
    # Arduino test_title_band: 13 cells kept at the cap for both kinds of text.
    s, raw = panel()
    s.title("acemnorsuvwxz")
    thirteen = lit(raw)
    assert box(raw, GRAY) == (18, 67, 221, 76)  # rows 63..78, ink from row 4
    s, raw = panel()
    s.title("acemnorsuvwxzacemnor")
    assert lit(raw) == thirteen


class RecordingDisplay:
    """A 240 px display that records draw_scaled_text and text calls."""

    width = height = 240

    def __init__(self):
        self.calls = []

    def text(self, s, x, y, c):
        self.calls.append(("text", s, x, y, 1))

    def draw_scaled_text(self, s, x, y, c, scale):
        self.calls.append(("scaled", s, x, y, scale))

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


def test_mock_long_title_draws_only_glyphs_inside_the_circle(mods):
    # Review Focus 1: a 22-character title at 240 raises nothing and keeps only
    # whole glyph cells that lie inside the circle at the title row.
    steami_screen, _ = mods
    d = RecordingDisplay()
    s = steami_screen.Screen(d)
    s.title("A very long title text")
    assert len(d.calls) == 1
    kind, text, x, y, scale = d.calls[0]
    assert (kind, scale, y) == ("scaled", 2, 63)  # at the cap row
    assert text == "A very long title text"[: len(text)]
    assert len(text) == 13
    for i in range(len(text)):
        x0, x1 = x + 16 * i, x + 16 * i + 15
        for px in (x0, x1):
            for py in (y, y + 15):
                assert (px - 120) ** 2 + (py - 120) ** 2 <= 120 * 120


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


def test_mock_widget_text_is_scaled_by_k(mods):
    steami_screen, _ = mods
    d = RecordingDisplay()
    s = steami_screen.Screen(d)
    s.title("Hi")
    s.text("Hi", at="NE")
    s.text("Hi", at="S", scale=2)
    s.value(42)
    s.text("xy", at=(10, 20))  # real pixels: not scaled
    s.text("xy", at=(10, 20), scale=3)
    assert [c[4] for c in d.calls] == [2, 2, 4, 4, 1, 3]
    assert d.calls[4][0] == "text"


# ----- subtitle -----

# Arduino kSubtitles[240]: the DARK ink box of each line.
SUBTITLES_240 = (
    (("WSEN-HIDS",), ((50, 202, 189, 215),)),
    (("BME280",), ((74, 202, 165, 215),)),
    (("SURPRISED",), ((50, 202, 189, 215),)),
    (("Comfortable",), ((34, 188, 205, 201),)),
    (("VL53L1X ToF",), ((34, 188, 205, 201),)),
    (("Uncomfortable",), ((18, 166, 221, 179),)),
    (("20s window",), ((42, 196, 199, 209),)),
    (("3842 mV", "BQ27441"), ((66, 177, 173, 190), (66, 197, 173, 210))),
    (("Comfortable", "WSEN-HIDS"), ((34, 173, 205, 186), (50, 193, 189, 206))),
    (("Uncomfortable", "WSEN-HIDS"), ((18, 151, 221, 164), (50, 171, 189, 184))),
    (("WSEN-HIDS", "20s window"), ((50, 176, 189, 189), (42, 196, 199, 209))),
    (("Uncomfortable", "BME280"), ((18, 151, 221, 164), (74, 171, 165, 184))),
    (("BME280", "20s window"), ((74, 176, 165, 189), (42, 196, 199, 209))),
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


def test_mock_value_center_with_unit_and_offset(panel):
    # Arduino kValues "72", "%", CENTER, yOffset -12: block 8f + 8f/3 + 8k = 58 at
    # f 4, top 120 + u(-12) - 29 = 69; the unit 8x8 x k at top + 8f.
    s, raw = panel()
    s.value(72, unit="%", y_offset=-12)
    assert box(raw, WHITE) == (92, 69, 147, 96)
    assert box(raw, LIGHT) == (114, 101, 125, 114)


def test_mock_value_center_default(panel):
    # rule: f = 2k = 4, no unit: top cy - 8f/2 = 104, centred 120 - 64/2 = 88
    # ("42": '4' inks from column 1, '2' up to column 6, rows 0-6, at x4 ->
    # 92..147, 104..131).
    s, raw = panel()
    s.value(42)
    assert box(raw, WHITE) == (92, 104, 147, 131)


# Arduino kSides[240]: value(text, unit, W or E) alone (texts without '.' or ':',
# whose width MicroPython and Arduino measure alike).
SIDES_240 = {
    "1": ((51, 96, 68, 116), (172, 96, 189, 116)),
    "8888": ((15, 96, 104, 116), (136, 96, 225, 116)),
    "123456": ((13, 102, 104, 115), (135, 102, 226, 115)),
}


@pytest.mark.parametrize("text", sorted(SIDES_240))
def test_mock_value_side_by_side(panel, text):
    for at, expected in zip(("W", "E"), SIDES_240[text]):
        s, raw = panel()
        s.value(text, unit="C", at=at)
        assert box(raw, WHITE) == expected, at


def test_mock_value_side_is_cut_at_scale_1(panel):
    # Arduino test_value_truncation: "Uncomfortable" whole at W, 15 glyphs cut to 14.
    s, raw = panel()
    s.value("Uncomfortable", unit="C", at="W")
    assert box(raw, WHITE) == (8, 107, 109, 113)
    s, raw = panel()
    s.value("ABCDEFGHIJKLMNO", unit="C", at="W")
    assert box(raw, WHITE) == (4, 107, 113, 113)


def test_mock_value_center_cut_near_the_edge(panel):
    # Arduino test_value_truncation: 15 '8' with a unit at yOffset -50 keep 13 glyphs.
    s, raw = panel()
    s.value("888888888888888", unit="C", y_offset=-50)
    assert box(raw, WHITE) == (69, 14, 170, 20)


def test_mock_value_label_and_unit_stay_in_their_half(panel):
    # rule: label 8x8 x k at top - u(4) - 8k; at W the label and unit are cut to
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


@pytest.mark.parametrize(
    "args,kwargs",
    (
        ((8, "C", "NE", "TEMP"), {"scale": 1}),
        ((8, "C", "NW", "TEMP"), {"scale": 1}),
        (("Temperature",), {"at": "N", "label": "X", "scale": 1}),
    ),
)
def test_mock_value_label_kept_when_the_value_falls_to_factor_1(panel, args, kwargs):
    # At N/NE/NW the value falls to factor 1 on row 22; the label's rows
    # 22 - u(4) - 16 = -1.. leave the circle, so it is lowered (never into the
    # value's rows) instead of being dropped.
    s, raw = panel()
    s.value(*args, **kwargs)
    label = box(raw, GRAY)
    assert label is not None
    assert label[3] < 22
    assert box(raw, WHITE)[1] == 22
    assert not outside(raw, slack=0)


def test_mock_value_label_row_unchanged_when_it_fits(panel):
    # rule: the label top stays at value top - u(4) - 8k when it fits.
    s, raw = panel()
    s.value(8, "C", "NE", "TEMP")
    assert box(raw, GRAY)[1] == box(raw, WHITE)[1] - 7 - 16


# ----- bar, gauge -----


def test_mock_bar_at_240(panel):
    # Arduino test_bar_golden: W - u(40) = 165 wide from x 38, u(8) = 15 rows from
    # cy + u(20) + u(-12) = 135; fill int(165 * 72 / 100) = 118 columns. The
    # track is DARK in MicroPython (GRID_DARK in Arduino).
    s, raw = panel()
    s.bar(72, 100, -12, color=(119, 255, 119))
    assert box(raw, GREEN) == (38, 135, 155, 149)
    assert count(raw, GREEN) == 118 * 15
    assert box(raw, DARK) == (156, 135, 202, 149)
    assert count(raw, DARK) == 47 * 15


def test_mock_gauge_ring_at_240(panel):
    # Arduino test_gauge_ring: outer radius radius - u(4) = 113, thickness
    # max(5, radius // 9) = 13: rows 7..19 at the top of the centre column.
    s, raw = panel()
    s.gauge(0)
    px = lit(raw)
    assert [y for y in range(40) if px.get((120, y)) == DARK] == list(range(7, 20))
    # Arduino test_gauge_labels_golden: the labels' top row 169 at distance
    # outer - 13 - u(10) = 82, angle 233 (min) and 127 (max); "0" centred on x 55.
    assert box(raw, GRAY)[:2] == (49, 169)
    # rule: "100" is 8x8 x k (5x7 in Arduino): centred on 185, cells 161..208.
    assert box(raw, GRAY)[2:] == (206, 182)
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
    # Arduino test_watch_numbers_golden: "12", "3", "6", "9" at R - u(15) = 77.
    s, raw = panel()
    s.watch(1, 37, 5)
    assert box(raw, WHITE) == (37, 35, 202, 202)
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
    # Arduino: the N letter centred at R + u(5) = 107 above the centre.
    assert box(raw, WHITE) == (114, 5, 125, 18)
    assert not outside(raw, slack=0)


# ----- menu, graph -----


def test_mock_menu_shows_five_rows_inside_the_circle(panel):
    # Arduino section 5.9 menu: rows u(35 + 14 j), a row is used when the chord at
    # its cell rows holds 12 cells (192 px): 5 rows on 240 (MicroPython: 6 on 128).
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
    # rule: value "90" 8x8 x k centred on cx at row u(31) = 58.
    assert box(raw, WHITE) == (106, 58, 133, 71)
    # rule: the labels sit inside the box (right of the axis), not left of it.
    labels = [p for p, c in lit(raw).items() if c == DARK and p[0] > 41 and p[1] < 168]
    assert labels and min(p[0] for p in labels) >= 39 + 2 + 3
    assert box(raw, GREEN) is not None
    assert not outside(raw, slack=0)


@pytest.mark.parametrize("max_val,labels", ((100, 3), (2000, 3)))
def test_mock_graph_labels_clear_the_axes_at_240(panel, max_val, labels):
    # Arduino 5.9: the labels sit inside the box, clear of its lines. Box rows
    # u(38) = 71 .. 71 + u(52) = 168; bottom axis rows 168-169 (k = 2), dashed
    # mid line row 71 + 48 = 119. Max label top 71 + u(2) = 74; the mid and min
    # labels' last inked row k + u(2) = 5 above their line: 114 and 163.
    s, raw = panel()
    s.graph([], min_val=0, max_val=max_val)
    rows = sorted({y for (x, y), c in lit(raw).items() if c == DARK and x >= 44 and y < 168})
    bands = [(74, 87), (101, 114), (150, 163)]
    assert all(any(a <= y <= b for a, b in bands) for y in rows), rows
    assert [any(a <= y <= b for y in rows) for a, b in bands] == [True] * labels
    assert not {119, 168, 169} & set(rows)
    px = lit(raw)
    # The dashes and the axis cross no label: rows 119 and 168 keep their own
    # colour only, and no label pixel touches the row next to them.
    assert {px[(x, 119)] for x in range(41, 76) if (x, 119) in px} == {GRID_DARK}
    assert not [y for y in rows if y in (118, 120, 167)]


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


def test_mock_radius_and_isqrt_never_fail(panel):
    s, _raw = panel()
    for y in (-500, -1, 0, 119, 120, 239, 240, 500):
        s._chord(y, y)
    assert s._chord(-1, 0) is None
    assert s._chord(41, 41) == (30, 210)
    assert s._chord(1, 14) == (105, 135)
    assert s._chord(63, 63)[1] - s._chord(63, 63)[0] + 1 == 211
    assert math.isclose(s.u(64), 120)
