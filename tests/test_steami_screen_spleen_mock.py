"""Mock tests of the generated Spleen font module of steami_screen.

spleen.py is generated (never hand-edited): these tests pin the file
itself and the contract the font helpers rely on.
"""

import hashlib
import importlib
import sys
from pathlib import Path

import pytest

from tests.runner.executor import cleanup_driver, load_driver_mock
from tests.test_steami_screen_scaling_mock import (  # noqa: F401 (mods and panel are fixtures)
    ANCHORS,
    WHITE,
    RecordingDisplay,
    box,
    lit,
    mods,
    panel,
)

ROOT = Path(__file__).parent.parent
SPLEEN_PATH = ROOT / "lib" / "steami_screen" / "steami_screen" / "spleen.py"
SPLEEN_SHA256 = "c550418ca14a68ca0cb18bdbce2e3eeafb544830d77ce41c601df8a00303ae30"


@pytest.fixture
def sp():
    """The steami_screen.spleen module, imported on CPython."""
    load_driver_mock("steami_screen", None)
    yield importlib.import_module("steami_screen.spleen")
    cleanup_driver("steami_screen")


@pytest.fixture
def fonts(sp):
    """The steami_screen.fonts module, imported after the spleen fixture."""
    return importlib.import_module("steami_screen.fonts")


def _named(sp, result):
    """(face name, n) of a face() result, the face matched by identity."""
    if result is None:
        return None
    names = {
        id(sp.F6X12): "F6X12",
        id(sp.F8X16): "F8X16",
        id(sp.F12X24): "F12X24",
        id(sp.F16X32): "F16X32",
    }
    return names[id(result[0])], result[1]


def test_mock_spleen_is_the_generated_file():
    data = SPLEEN_PATH.read_bytes()
    assert hashlib.sha256(data).hexdigest() == SPLEEN_SHA256
    assert data.split(b"\n", 1)[0] == b"# SPDX-License-Identifier: BSD-2-Clause"


def test_mock_spleen_contract(sp):
    assert sp.VERSION == "2.1.0"
    assert sp.VALUE_KEY == " +-.:0123456789"
    assert len(sp.EXTRA) == len(sp.FOLD) == 33
    assert sp.FOLD[0] == "°"
    assert sp.FOLD[32] == "Y"
    assert sp.F6X12[:4] == (6, 12, 9, None)
    assert sp.F8X16[:4] == (8, 16, 12, None)
    assert sp.F12X24[:4] == (12, 24, 19, sp.VALUE_KEY)
    assert sp.F16X32[:4] == (16, 32, 26, sp.VALUE_KEY)
    faces = (sp.F6X12, sp.F8X16, sp.F12X24, sp.F16X32)
    assert [len(f[4]) for f in faces] == [1536, 2048, 720, 960]
    for face in faces:
        assert isinstance(face[4], bytes)


def test_mock_fold_copy_matches_spleen(sp, fonts):
    assert fonts.EXTRA == sp.EXTRA
    assert fonts.FOLD8[1:] == sp.FOLD[1:]
    assert fonts.FOLD8[0] == "\x7f"
    assert all(ord(ch) < 128 for ch in fonts.FOLD8)


@pytest.mark.parametrize(
    ("ch", "expected"),
    [
        (" ", 32),
        ("~", 126),
        ("°", 127),
        ("À", 128),
        ("é", 148),
        ("Ÿ", 159),
        ("€", 63),
        ("ñ", 63),
        ("\n", 63),
        ("\x7f", 63),
    ],
)
def test_mock_code_of_a_character(fonts, ch, expected):
    assert fonts.code(ch) == expected


def test_mock_fold8(fonts):
    assert fonts.fold8("Été 23°C") == "Ete 23\x7fC"
    assert fonts.fold8("Ÿ€ñ") == "Y€ñ"
    assert fonts.fold8("a\tb\x7f\n") == "a\tb\x7f\n"


def test_mock_face_ladder(sp, fonts):
    value, label, text = fonts.VALUE, fonts.LABEL, fonts.TEXT
    assert [_named(sp, fonts.face("23.5", value, f)) for f in range(1, 13)] == [
        None,
        ("F8X16", 1),
        ("F12X24", 1),
        ("F16X32", 1),
        None,
        ("F12X24", 2),
        None,
        ("F16X32", 2),
        ("F12X24", 3),
        ("F8X16", 5),
        None,
        ("F16X32", 3),
    ]
    assert _named(sp, fonts.face("12:30 PM", value, 2)) == ("F8X16", 1)
    assert fonts.face("12:30 PM", value, 3) is None
    assert _named(sp, fonts.face("12:30 PM", value, 4)) == ("F8X16", 2)
    assert _named(sp, fonts.face("", value, 4)) == ("F16X32", 1)
    assert _named(sp, fonts.face("Été", value, 4)) == ("F8X16", 2)
    assert _named(sp, fonts.face("TEMP", label, 2)) == ("F6X12", 1)
    assert _named(sp, fonts.face("TEMP", label, 4)) == ("F6X12", 1)
    assert _named(sp, fonts.face("Hi", text, 2)) == ("F8X16", 1)
    assert _named(sp, fonts.face("Hi", text, 6)) == ("F8X16", 3)
    assert fonts.face("Hi", text, 3) is None


def test_mock_glyph_offsets(sp, fonts):
    assert fonts.offset(sp.F8X16, "A") == 528
    assert fonts.offset(sp.F8X16, "é") == 1856
    assert fonts.offset(sp.F16X32, ".") == 192
    assert fonts.offset(sp.F12X24, "9") == 672
    o = fonts.offset(sp.F6X12, "Ÿ")
    p = fonts.offset(sp.F6X12, "Y")
    assert sp.F6X12[4][o : o + 12] == sp.F6X12[4][p : p + 12]


def test_mock_widths(fonts):
    value, label, text = fonts.VALUE, fonts.LABEL, fonts.TEXT
    assert fonts.width("12:30 PM", 8, value, 2) == 60
    assert fonts.width("23.5", 4, value, 4) == 56
    assert fonts.width("23.5", 4, value, 2) == 28
    assert fonts.width("TEMP", 4, label, 2) == 24
    assert fonts.width("Hi", 2, text, 2) == 16
    assert fonts.width("a.b", 3, text, 2) == 24
    assert fonts.width("1.5", 2, value, 4) == 24
    assert fonts.width("1.5", 0, value, 4) == 0
    assert fonts.widths("1.5", value, 4) == [16, 24, 40]
    assert fonts.widths("", text, 2) == []
    assert fonts.advance(value, 4) == 16


def test_mock_masks_and_ink_rows(sp, fonts):
    assert fonts.masks(sp.F6X12, "TEMP")[-1] == 0x1FE
    assert fonts.masks(sp.F8X16, "Hg")[-1] == 0x7FFC
    assert fonts.ink_rows(fonts.masks(sp.F16X32, "8")[-1]) == (6, 25)
    assert fonts.ink_rows(fonts.masks(sp.F12X24, "8")[-1]) == (4, 18)
    assert fonts.masks(sp.F8X16, "É")[-1] & 1 == 1
    assert fonts.masks(sp.F8X16, " ") == [0]
    assert fonts.masks(sp.F8X16, "") == []
    assert fonts.masks(sp.F16X32, "8") == fonts.masks(sp.F16X32, "8")


def test_mock_draw_runs_one_call_per_run(fonts):
    c = 7
    rec = []

    def fr(x, y, w, h, colour):
        rec.append((x, y, w, h, colour))

    glyphs = [(0, 10, 20)]
    fonts.draw_runs(fr, (8, 1, 0, None, b"\xb0"), glyphs, 2, 0, c)
    assert rec == [(10, 20, 2, 2, c), (14, 20, 4, 2, c)]
    rec.clear()
    fonts.draw_runs(fr, (8, 1, 0, None, b"\xb0"), glyphs, 2, 1, c)
    assert rec == [(10, 20, 4, 2, c), (14, 20, 6, 2, c)]
    rec.clear()
    fonts.draw_runs(fr, (16, 1, 0, None, b"\x80\x01"), glyphs, 1, 0, c)
    assert rec == [(10, 20, 1, 1, c), (25, 20, 1, 1, c)]
    rec.clear()
    fonts.draw_runs(fr, (8, 1, 0, None, b"\x00"), glyphs, 1, 0, c)
    assert rec == []
    fonts.draw_runs(fr, fonts.DEGREE8, glyphs, 1, 0, c)
    assert rec == [
        (12, 20, 2, 1, c),
        (11, 21, 1, 1, c),
        (14, 21, 1, 1, c),
        (11, 22, 1, 1, c),
        (14, 22, 1, 1, c),
        (12, 23, 2, 1, c),
    ]


def test_mock_fonts_loads_spleen_only_for_a_face():
    load_driver_mock("steami_screen", None)
    try:
        fonts = importlib.import_module("steami_screen.fonts")
        fonts.code("é")
        fonts.fold8("Été 23°C")
        fonts.width("23.5", 4, fonts.VALUE, 4)
        fonts.advance(fonts.TEXT, 2)
        fonts.draw_runs(lambda *args: None, fonts.DEGREE8, [(0, 0, 0)], 1, 0, 1)
        assert "steami_screen.spleen" not in sys.modules
        fonts.face("A", fonts.TEXT, 2)
        assert "steami_screen.spleen" in sys.modules
    finally:
        cleanup_driver("steami_screen")


# ----- Pixel text on 240: Spleen 8x16 x scale -----

RGB_WHITE = (255, 255, 255)


@pytest.fixture
def psp(mods):  # noqa: F811 (the imported fixture)
    """The steami_screen.spleen module of the `mods` context."""
    return importlib.import_module("steami_screen.spleen")


def spleen_pixels(fc, s, x, y, n):
    """Set of the pixels of s drawn in face fc at (x, y), n x n per font pixel.

    Read from the spleen.py bytes directly (MSB = column 0), not through
    fonts: a full set maps ASCII 32..126, then EXTRA from 127, else '?';
    a value set looks its key up. Each cell advances w * n.
    """
    w, h, key, data = fc[0], fc[1], fc[3], fc[4]
    extra = sys.modules["steami_screen.spleen"].EXTRA
    bpr = (w + 7) // 8
    out = set()
    for ch in s:
        if key is not None:
            i = key.find(ch)
        elif 32 <= ord(ch) <= 126:
            i = ord(ch) - 32
        elif ch in extra:
            i = 95 + extra.find(ch)
        else:
            i = ord("?") - 32
        o = i * h * bpr
        for r in range(h):
            for col in range(w):
                if data[o + r * bpr + col // 8] >> (7 - col % 8) & 1:
                    for dy in range(n):
                        for dx in range(n):
                            out.add((x + col * n + dx, y + r * n + dy))
        x += w * n
    return out


def on_panel(pixels, size=240):
    """{(x, y): WHITE} of the pixels that lie on a size x size panel."""
    return {p: WHITE for p in pixels if 0 <= p[0] < size and 0 <= p[1] < size}


def counting(screen, raw):
    """Count raw.blit and fill_rect calls of screen's GC9A01 adapter.

    Apply before the first draw on that screen. Returns the live counts.
    """
    n = {"blit": 0, "fill_rect": 0}
    blit, fill_rect = raw.blit, screen._d._fill_rect_raw

    def counted_blit(*args):
        n["blit"] += 1
        return blit(*args)

    def counted_fill_rect(*args):
        n["fill_rect"] += 1
        return fill_rect(*args)

    raw.blit = counted_blit
    screen._d._fill_rect_raw = counted_fill_rect
    return n


def test_mock_text_height_and_max_chars(panel):  # noqa: F811
    s, _ = panel(128)
    assert [s.text_height(), s.text_height(2), s.text_height(0)] == [8, 16, 8]
    assert s.max_chars == 16
    s, _ = panel(240)
    assert [s.text_height(), s.text_height(2), s.text_height(0)] == [16, 32, 16]
    assert s.max_chars == 30


ACCENTED = "Élève 12:3.5°Ÿ"


@pytest.mark.parametrize("scale", (1, 2, 3))
def test_mock_pixel_text_matches_the_spleen_rows(panel, psp, scale):  # noqa: F811
    # ':' and '.' are full 8x16 cells (no narrow window, no bold, 5.3);
    # 'Ÿ' comes from slot 159.
    s, raw = panel(240)
    s.text(ACCENTED, at=(5, 30), color=RGB_WHITE, scale=scale)
    pixels = spleen_pixels(psp.F8X16, ACCENTED, 5, 30, scale)
    assert lit(raw) == on_panel(pixels)
    if scale == 1:
        assert len(pixels) == 342
        assert box(raw) == (5, 30, 115, 41)
    elif scale == 2:
        assert len(pixels) == 1368
        assert box(raw) == (5, 30, 226, 53)
    else:
        assert max(p[0] for p in pixels) > 239  # clipped at the right edge
        assert box(raw)[2] == 239


def test_mock_pixel_text_unknown_character_is_a_question_mark(panel):  # noqa: F811
    s, raw = panel(240)
    s.text("€5", at=(0, 0))
    euro = lit(raw)
    s, raw = panel(240)
    s.text("?5", at=(0, 0))
    assert euro
    assert euro == lit(raw)


def test_mock_pixel_text_clips_at_the_panel_edges(panel, psp):  # noqa: F811
    for text, at, scale in (
        ("Hello", (-5, 230), 2),
        ("Hi", (235, -10), 3),
        ("Hi", (-3, 232), 1),
        ("Hi", (236, -6), 1),
    ):
        s, raw = panel(240)
        s.text(text, at=at, scale=scale)
        pixels = spleen_pixels(psp.F8X16, text, at[0], at[1], scale)
        assert lit(raw) == on_panel(pixels), (text, at, scale)
        assert lit(raw), (text, at, scale)
    for scale in (1, 2):
        s, raw = panel(240)
        s.text("A", at=(300, 300), scale=scale)
        assert lit(raw) == {}


def test_mock_pixel_text_call_counts(panel):  # noqa: F811
    s, raw = panel(240)
    n = counting(s, raw)
    s.text("Hi", at=(0, 0))
    assert n == {"blit": 2, "fill_rect": 0}
    s, raw = panel(240)
    n = counting(s, raw)
    s.text("Hi", at=(0, 0), scale=2)
    # One fill_rect per run: 19 for 'H' and 9 for 'i', fewer than 252 // 4.
    assert n == {"blit": 0, "fill_rect": 28}


def test_mock_draw_value_ink_is_narrow_and_bold(mods, psp):  # noqa: F811
    steami_screen, _ = mods
    fonts = sys.modules["steami_screen.fonts"]
    d = RecordingDisplay()
    s = steami_screen.Screen(d)
    o8, odot = fonts.offset(psp.F16X32, "8"), fonts.offset(psp.F16X32, ".")
    s._draw("8.8", 100, 50, RGB_WHITE, fonts.VALUE, 4)
    s._draw("8.8", 100, 50, RGB_WHITE, fonts.VALUE, 8)
    s._draw("12:30 PM", 0, 0, RGB_WHITE, fonts.VALUE, 2)
    s._draw("a.b", 0, 0, RGB_WHITE, fonts.TEXT, 2)
    assert d.calls[0] == ("glyphs", 16, 32, [(o8, 100, 50), (odot, 112, 50), (o8, 124, 50)], 1, 1)
    assert d.calls[1] == ("glyphs", 16, 32, [(o8, 100, 50), (odot, 124, 50), (o8, 148, 50)], 2, 1)
    kind, w, h, glyphs, n, bold = d.calls[2]
    assert (kind, w, h, n, bold) == ("glyphs", 8, 16, 1, 0)
    assert [g[1] for g in glyphs] == [0, 8, 14, 20, 28, 36, 44, 52]
    assert glyphs[2][0] == fonts.offset(psp.F8X16, ":")
    kind, w, h, glyphs, n, bold = d.calls[3]
    assert (kind, w, h, n, bold) == ("glyphs", 8, 16, 1, 0)
    assert [g[1] for g in glyphs] == [0, 8, 16]


def test_mock_draw_without_draw_glyphs_fills_runs(mods, psp):  # noqa: F811
    # A display without draw_glyphs gets fonts.draw_runs over Screen._fill_rect.
    steami_screen, _ = mods

    class RectDisplay:
        width = height = 240

        def __init__(self):
            self.rects = []

        def fill_rect(self, *args):
            self.rects.append(args)

    d = RectDisplay()
    s = steami_screen.Screen(d)
    s.text("Hi", at=(0, 0))
    pixels = set()
    for x, y, w, h, c in d.rects:
        assert c == RGB_WHITE
        pixels.update((x + i, y + j) for i in range(w) for j in range(h))
    assert len(d.rects) == 28  # one per run: 19 for 'H' and 9 for 'i'
    assert pixels == spleen_pixels(psp.F8X16, "Hi", 0, 0, 1)


def test_mock_cut_value_text_keeps_the_face_of_the_whole_text(mods, psp):  # noqa: F811
    # Design 5.1: the face is judged on the whole text. "12:30 PM" at f 4 is
    # 8x16 x 2 (TEXT ladder, not bold); its cut prefix "12:3" (16 + 16 + 8 + 16
    # = 56 px) keeps that face, never 16x32 judged from the digits. The room
    # is [2, 60]: the chord at the ink rows 104..123 starts at x 2, so "12:30"
    # (72 px) is cut and the narrow ':' sits 4 px left of its pen.
    steami_screen, _ = mods
    fonts = sys.modules["steami_screen.fonts"]
    d = RecordingDisplay()
    s = steami_screen.Screen(d)
    s._put("12:30 PM", 0, 100, RGB_WHITE, fonts.VALUE, 4, 0, 0, 60)
    o = {ch: fonts.offset(psp.F8X16, ch) for ch in "123:"}
    assert d.calls == [
        (
            "glyphs",
            8,
            16,
            [(o["1"], 2, 100), (o["2"], 18, 100), (o[":"], 30, 100), (o["3"], 42, 100)],
            2,
            0,
        )
    ]


def test_mock_native_widget_text_is_one_blit_per_glyph(panel):  # noqa: F811
    s, raw = panel(240)
    n = counting(s, raw)
    s.title("Distance")
    assert n == {"blit": 8, "fill_rect": 0}
    s, raw = panel(240)
    n = counting(s, raw)
    s.subtitle("VL53L1X ToF")
    assert n["blit"] == 11
    s, raw = panel(240)
    n = counting(s, raw)
    s.gauge(342, 0, 500)
    assert n["blit"] == 4


def test_mock_128_never_touches_spleen(panel):  # noqa: F811
    s, raw = panel(128)
    n = counting(s, raw)
    s.title("Title")
    s.value(21.5, unit="C", label="T")
    s.subtitle("one", "two")
    s.bar(40)
    s.gauge(30)
    s.graph([1, 5, 3, 8])
    s.menu(["a", "b", "c"], selected=1)
    s.compass(90)
    s.watch(10, 30, 15)
    s.face("happy")
    for scale in (1, 2):
        for at in (*ANCHORS, (3, 4)):
            s.text("Hi", at=at, scale=scale)
    assert lit(raw)
    assert "steami_screen.spleen" not in sys.modules
    assert n["blit"] == 0
