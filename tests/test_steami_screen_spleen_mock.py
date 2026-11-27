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
