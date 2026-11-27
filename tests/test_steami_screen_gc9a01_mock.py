"""Mock tests of the GC9A01Display adapter of steami_screen.

The adapter turns RGB tuples (or legacy grey4 ints) into the 16-entry
palette indexes of the gc9a01 driver. Pixel tests run on the real driver
frame (GS4_HMSB) built on a FakeSPI; forwarding tests use a recording raw.
"""

import importlib
import sys

import pytest

from tests.fake_machine import FakePin, FakeSPI
from tests.fake_machine.font_petme128 import FONT_PETME128_8X8
from tests.runner.executor import cleanup_driver, load_driver_mock

# Named colours of steami_screen and their palette index.
NAMED = {
    "BLACK": ((0, 0, 0), 0),
    "GRID_DARK": ((51, 51, 51), 1),
    "DARK": ((102, 102, 102), 2),
    "GRAY": ((153, 153, 153), 3),
    "LIGHT": ((187, 187, 187), 4),
    "WHITE": ((255, 255, 255), 5),
    "GREEN": ((119, 255, 119), 6),
    "RED": ((255, 85, 85), 7),
    "BLUE": ((85, 85, 255), 8),
    "YELLOW": ((255, 255, 85), 9),
    "CYAN": ((85, 255, 255), 10),
    "MAGENTA": ((255, 85, 255), 11),
    "ORANGE": ((255, 165, 0), 12),
    "DARK_GREEN": ((0, 128, 0), 13),
    "DARK_RED": ((128, 0, 0), 14),
    "DARK_BLUE": ((0, 0, 128), 15),
}


def driver_palette():
    """PALETTE of the gc9a01 driver (the single source of truth)."""
    return tuple(map(tuple, importlib.import_module("gc9a01.const").PALETTE))


def nearest(rgb):
    """Index of the palette entry nearest to rgb (squared RGB distance)."""
    palette = driver_palette()
    return min(
        range(16),
        key=lambda i: sum((a - b) ** 2 for a, b in zip(palette[i], rgb)),
    )


class RecordingRaw:
    """A raw driver that records every call."""

    def __init__(self):
        self.width = 240
        self.height = 240
        self.calls = []

    def fill(self, i):
        self.calls.append(("fill", i))

    def pixel(self, x, y, i=None):
        self.calls.append(("pixel", x, y, i))

    def text(self, s, x, y, i):
        self.calls.append(("text", s, x, y, i))

    def line(self, x1, y1, x2, y2, i):
        self.calls.append(("line", x1, y1, x2, y2, i))

    def fill_rect(self, x, y, w, h, i):
        self.calls.append(("fill_rect", x, y, w, h, i))

    def rect(self, x, y, w, h, i):
        self.calls.append(("rect", x, y, w, h, i))

    def show(self):
        self.calls.append(("show",))

    def blit(self, fb, x, y, key=-1, palette=None):
        self.calls.append(
            (
                "blit",
                bytes(fb[0]),
                fb[1],
                fb[2],
                fb[3],
                x,
                y,
                key,
                (palette.pixel(0, 0), palette.pixel(1, 0)),
            )
        )


@pytest.fixture
def mods():
    """The steami_screen package and the gc9a01 driver, on CPython."""
    load_driver_mock("steami_screen", None)
    module, _ = load_driver_mock("gc9a01", None)
    yield sys.modules["steami_screen"], module
    cleanup_driver("gc9a01")
    cleanup_driver("steami_screen")


@pytest.fixture
def adapter_mod(mods):
    import steami_screen.gc9a01 as adapter_mod

    return adapter_mod


@pytest.fixture
def real(mods):
    """A GC9A01Display on the real driver (FakeSPI, no reset pin)."""
    steami_screen, driver = mods
    raw = driver.GC9A01(FakeSPI(1), FakePin("dc"), FakePin("cs"))
    return steami_screen.GC9A01Display(raw), raw


@pytest.fixture
def recorded(mods):
    steami_screen, _ = mods
    raw = RecordingRaw()
    return steami_screen.GC9A01Display(raw), raw


# ----- Colour mapping -----


@pytest.mark.parametrize("name", sorted(NAMED))
def test_named_colour_maps_to_its_exact_index(adapter_mod, name):
    rgb, index = NAMED[name]
    assert adapter_mod.rgb_to_index(rgb) == index


def test_nearest_colour_by_squared_rgb_distance(adapter_mod):
    # Review Focus 2: (200, 100, 50) is not in the palette. Squared distance
    # to ORANGE (255,165,0) is 55^2 + 65^2 + 50^2 = 9750, to DARK_RED
    # (128,0,0) 72^2 + 100^2 + 50^2 = 17684, to RED (255,85,85) 55^2 + 15^2 +
    # 35^2 = 4475, the smallest.
    expected = nearest((200, 100, 50))
    assert expected == 7
    assert adapter_mod.rgb_to_index((200, 100, 50)) == expected


def test_nearest_matches_brute_force_on_a_colour_grid(adapter_mod):
    for r in range(0, 256, 51):
        for g in range(0, 256, 51):
            for b in range(0, 256, 51):
                assert adapter_mod.rgb_to_index((r, g, b)) == nearest((r, g, b))


def test_legacy_int_is_a_grey4_level_mapped_to_the_nearest_grey(adapter_mod):
    # colors.py gives an int the meaning grey4: level n is the grey n * 17
    # (R = G = B). The adapter maps it to the palette entry nearest to it,
    # except that a non-zero level is never BLACK (see the next test).
    assert adapter_mod.rgb_to_index(15) == 5  # 255 -> WHITE
    assert adapter_mod.rgb_to_index(0) == 0  # 0 -> BLACK
    for level in range(2, 16):
        grey = level * 17
        assert adapter_mod.rgb_to_index(level) == nearest((grey, grey, grey))
    # The values the old constants rely on.
    assert adapter_mod.rgb_to_index(6) == 2  # 102 -> DARK
    assert adapter_mod.rgb_to_index(9) == 3  # 153 -> GRAY
    assert adapter_mod.rgb_to_index(11) == 4  # 187 -> LIGHT


def test_non_zero_grey4_level_is_never_black(adapter_mod):
    # Level 1 (grey 17) is nearest to BLACK, but it is visible on the SSD1327:
    # it becomes GRID_DARK, the darkest visible entry. The RGB tuple keeps the
    # plain nearest rule, even after the int has been looked up.
    assert adapter_mod.rgb_to_index(1) == 1
    assert adapter_mod.rgb_to_index((17, 17, 17)) == 0
    assert adapter_mod.rgb_to_index(1) == 1
    assert all(adapter_mod.rgb_to_index(level) != 0 for level in range(1, 16))


def test_legacy_int_is_clamped_to_the_grey4_range(adapter_mod):
    assert adapter_mod.rgb_to_index(99) == 5
    assert adapter_mod.rgb_to_index(-3) == 0


def test_adapter_palette_matches_the_driver_palette(adapter_mod):
    # The adapter keeps its own copy (it must not import gc9a01): this test
    # catches any drift from gc9a01.const.PALETTE.
    assert driver_palette() == adapter_mod._PALETTE
    assert len(adapter_mod._PALETTE) == 16


def test_named_colours_are_the_driver_palette_entries(adapter_mod):
    palette = driver_palette()
    for rgb, index in NAMED.values():
        assert palette[index] == rgb


def test_adapter_does_not_import_the_driver(adapter_mod):
    import ast
    import inspect

    for node in ast.walk(ast.parse(inspect.getsource(adapter_mod))):
        if isinstance(node, ast.Import):
            assert not any(a.name.split(".")[0] == "gc9a01" for a in node.names)
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] != "gc9a01"


def test_mapping_is_repeatable_and_cached(adapter_mod):
    first = adapter_mod.rgb_to_index((200, 100, 50))
    assert (200, 100, 50) in adapter_mod._cache
    assert adapter_mod.rgb_to_index((200, 100, 50)) == first


def test_cache_stays_bounded_and_results_stay_correct(adapter_mod):
    for n in range(1000):
        color = (n % 256, (n * 7) % 256, (n * 13) % 256)
        assert adapter_mod.rgb_to_index(color) == nearest(color)
        assert len(adapter_mod._cache) <= adapter_mod._CACHE_MAX


# ----- Forwarding -----


def test_adapter_reports_the_raw_size(recorded):
    display, _ = recorded
    assert (display.width, display.height) == (240, 240)


def test_size_defaults_to_240(mods):
    steami_screen, _ = mods

    class Bare:
        framebuf = RecordingRaw()  # fill_rect reached through the frame

    display = steami_screen.GC9A01Display(Bare())
    assert (display.width, display.height) == (240, 240)


def test_every_method_forwards_to_the_raw_driver(recorded):
    display, raw = recorded
    red, white = (255, 85, 85), (255, 255, 255)
    display.fill(red)
    display.pixel(1, 2, white)
    display.text("hi", 3, 4, red)
    display.line(0, 1, 2, 3, white)
    display.fill_rect(5, 6, 7, 8, red)
    display.rect(9, 10, 11, 12, white)
    display.show()
    assert raw.calls == [
        ("fill", 7),
        ("pixel", 1, 2, 5),
        ("text", "hi", 3, 4, 7),
        ("line", 0, 1, 2, 3, 5),
        ("fill_rect", 5, 6, 7, 8, 7),
        ("rect", 9, 10, 11, 12, 5),
        ("show",),
    ]


def test_legacy_ints_are_mapped_before_forwarding(recorded):
    display, raw = recorded
    display.fill(15)
    display.rect(0, 0, 4, 4, 6)
    assert raw.calls == [("fill", 5), ("rect", 0, 0, 4, 4, 2)]


def test_methods_draw_on_the_real_frame(real):
    display, raw = real
    display.fill((0, 0, 0))
    display.pixel(10, 10, (255, 85, 85))
    display.fill_rect(20, 20, 3, 2, (0, 128, 0))
    display.rect(40, 40, 5, 5, (0, 0, 128))
    display.line(60, 60, 64, 60, (255, 255, 255))
    assert raw.framebuf.pixel(10, 10) == 7
    assert raw.framebuf.pixel(22, 21) == 13
    assert raw.framebuf.pixel(40, 40) == 15
    assert raw.framebuf.pixel(42, 42) == 0  # inside the outline
    assert raw.framebuf.pixel(62, 60) == 5


def test_text_draws_on_the_real_frame(real):
    display, raw = real
    display.fill(0)
    display.text("A", 0, 0, (255, 255, 255))
    glyph = FONT_PETME128_8X8[(ord("A") - 32) * 8 : (ord("A") - 32) * 8 + 8]
    for px in range(8):
        for py in range(8):
            assert raw.framebuf.pixel(px, py) == (5 if glyph[px] >> py & 1 else 0)


def test_show_forwards_to_the_real_driver(real):
    display, raw = real
    shown = []
    raw.show = lambda: shown.append(True)
    display.show()
    assert shown == [True]


# ----- draw_scaled_text -----


def lit(glyph, px, py):
    return bool(glyph[px] >> py & 1)


def test_scaled_text_doubles_the_glyph(real):
    display, raw = real
    display.fill((0, 0, 0))
    display.draw_scaled_text("A", 0, 0, (255, 255, 255), 2)
    glyph = FONT_PETME128_8X8[(ord("A") - 32) * 8 : (ord("A") - 32) * 8 + 8]
    for y in range(16):
        for x in range(16):
            want = 5 if lit(glyph, x // 2, y // 2) else 0
            assert raw.framebuf.pixel(x, y) == want, (x, y)
    # Nothing outside the 16 x 16 block.
    assert raw.framebuf.pixel(16, 0) == 0
    assert raw.framebuf.pixel(0, 16) == 0


def test_scaled_text_advances_by_eight_times_the_scale(real):
    display, raw = real
    display.fill(0)
    display.draw_scaled_text("AB", 10, 20, (255, 85, 85), 3)
    ga = FONT_PETME128_8X8[(ord("A") - 32) * 8 :][:8]
    gb = FONT_PETME128_8X8[(ord("B") - 32) * 8 :][:8]
    for y in range(24):
        for x in range(48):
            glyph, gx = (ga, x) if x < 24 else (gb, x - 24)
            want = 7 if lit(glyph, gx // 3, y // 3) else 0
            assert raw.framebuf.pixel(10 + x, 20 + y) == want, (x, y)


def test_scaled_text_goes_through_fill_rect_blocks(recorded):
    display, raw = recorded
    display.draw_scaled_text("A", 4, 6, (255, 255, 255), 2)
    assert raw.calls
    for call in raw.calls:
        assert call[0] == "fill_rect"
        assert call[3:] == (2, 2, 5)


# ----- draw_glyphs -----


@pytest.fixture
def sp(mods):
    """The steami_screen.spleen module, imported on CPython."""
    return importlib.import_module("steami_screen.spleen")


def glyph_bits(fc, o):
    """Set (col, row) bits of the glyph at offset o, MSB = column 0."""
    w, h, data = fc[0], fc[1], fc[4]
    bpr = (w + 7) // 8
    bits = set()
    for r in range(h):
        for col in range(w):
            if data[o + r * bpr + col // 8] >> (7 - col % 8) & 1:
                bits.add((col, r))
    return bits


def test_draw_glyphs_blits_native_faces_with_one_colour_lookup(
    recorded, adapter_mod, sp, monkeypatch
):
    display, raw = recorded
    lookups = []
    original = adapter_mod.rgb_to_index

    def counting(color):
        lookups.append(color)
        return original(color)

    monkeypatch.setattr(adapter_mod, "rgb_to_index", counting)
    data = bytes(sp.F8X16[4])
    # Offset 528 is "A", 1168 is "i".
    display.draw_glyphs(sp.F8X16, [(528, 10, 20), (1168, 18, 20)], 1, 0, (255, 255, 255))
    assert raw.calls == [
        ("blit", data[528:544], 8, 16, 3, 10, 20, 0, (0, 5)),
        ("blit", data[1168:1184], 8, 16, 3, 18, 20, 0, (0, 5)),
    ]
    assert len(lookups) == 1


def test_draw_glyphs_bold_is_a_second_blit_one_pixel_right(recorded, sp):
    display, raw = recorded
    o = sp.VALUE_KEY.find("8") * 32 * 2
    display.draw_glyphs(sp.F16X32, [(o, 50, 60)], 1, 1, (255, 255, 255))
    data = bytes(sp.F16X32[4])[o : o + 64]
    assert raw.calls == [
        ("blit", data, 16, 32, 3, 50, 60, 0, (0, 5)),
        ("blit", data, 16, 32, 3, 51, 60, 0, (0, 5)),
    ]


def test_draw_glyphs_black_uses_key_1(recorded, sp):
    display, raw = recorded
    display.draw_glyphs(sp.F8X16, [(528, 0, 0)], 1, 0, (0, 0, 0))
    assert len(raw.calls) == 1
    call = raw.calls[0]
    assert call[0] == "blit"
    assert call[7] == 1
    assert call[8] == (1, 0)


def test_draw_glyphs_fills_runs_for_replicated_faces(recorded, sp):
    display, raw = recorded
    o = 528 + 7 * 16  # "H"
    display.draw_glyphs(sp.F8X16, [(o, 10, 20)], 2, 0, (255, 255, 255))
    assert {call[0] for call in raw.calls} == {"fill_rect"}
    assert len(raw.calls) == 19
    assert all(call[4] == 2 and call[5] == 5 for call in raw.calls)
    assert raw.calls[:2] == [
        ("fill_rect", 10, 24, 4, 2, 5),
        ("fill_rect", 20, 24, 4, 2, 5),
    ]
    assert ("fill_rect", 10, 32, 14, 2, 5) in raw.calls

    raw.calls.clear()
    display.draw_glyphs(sp.F8X16, [(o, 10, 20)], 2, 1, (255, 255, 255))
    assert raw.calls[:2] == [
        ("fill_rect", 10, 24, 6, 2, 5),
        ("fill_rect", 20, 24, 6, 2, 5),
    ]


def test_draw_glyphs_keeps_the_background(real, sp):
    # Review Focus 1: only the glyph's set bits change, whatever the colour.
    display, raw = real
    fb = raw.framebuf
    bits = glyph_bits(sp.F8X16, 528)  # "A"
    assert len(bits) == 44

    def cell(x0, y0, n):
        """{(x, y): value} of the n-replicated 8x16 cell at x0, y0."""
        return {
            (x0 + x, y0 + y): fb.pixel(x0 + x, y0 + y) for y in range(16 * n) for x in range(8 * n)
        }

    def expected(x0, y0, n, ink, bg):
        return {
            (x0 + x, y0 + y): ink if (x // n, y // n) in bits else bg
            for y in range(16 * n)
            for x in range(8 * n)
        }

    display.fill((102, 102, 102))  # DARK, index 2
    display.draw_glyphs(sp.F8X16, [(528, 10, 20)], 1, 0, (255, 255, 255))
    got = cell(10, 20, 1)
    assert got == expected(10, 20, 1, 5, 2)
    assert sum(1 for v in got.values() if v == 2) == 84

    display.fill((255, 255, 255))
    display.draw_glyphs(sp.F8X16, [(528, 10, 20)], 1, 0, (0, 0, 0))
    assert cell(10, 20, 1) == expected(10, 20, 1, 0, 5)

    display.fill((255, 255, 255))
    display.draw_glyphs(sp.F8X16, [(528, 10, 20)], 2, 0, (0, 0, 0))
    assert cell(10, 20, 2) == expected(10, 20, 2, 0, 5)
    # Nothing around the cell is painted.
    assert fb.pixel(9, 20) == fb.pixel(26, 20) == fb.pixel(10, 52) == 5
