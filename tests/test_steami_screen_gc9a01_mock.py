"""Mock tests of the GC9A01Display adapter of steami_screen.

The adapter turns RGB tuples (or legacy grey4 ints) into the 16-entry
palette indexes of the gc9a01 driver. Pixel tests run on the real driver
frame (GS4_HMSB) built on a FakeSPI; forwarding tests use a recording raw.
"""

import sys

import pytest

from tests.fake_machine import FakePin, FakeSPI
from tests.fake_machine.font_petme128 import FONT_PETME128_8X8
from tests.runner.executor import cleanup_driver, load_driver_mock

# Palette of the global constraints (index: RGB).
PALETTE = (
    (0, 0, 0),
    (51, 51, 51),
    (102, 102, 102),
    (153, 153, 153),
    (187, 187, 187),
    (255, 255, 255),
    (119, 255, 119),
    (255, 85, 85),
    (85, 85, 255),
    (255, 255, 85),
    (85, 255, 255),
    (255, 85, 255),
    (255, 165, 0),
    (0, 128, 0),
    (128, 0, 0),
    (0, 0, 128),
)

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


def nearest(rgb):
    """Index of the palette entry nearest to rgb (squared RGB distance)."""
    best = min(
        range(16),
        key=lambda i: sum((a - b) ** 2 for a, b in zip(PALETTE[i], rgb)),
    )
    return best


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
    # (R = G = B). The adapter maps it to the palette entry nearest to it.
    assert adapter_mod.rgb_to_index(15) == 5  # 255 -> WHITE
    assert adapter_mod.rgb_to_index(0) == 0  # 0 -> BLACK
    for level in range(16):
        grey = level * 17
        assert adapter_mod.rgb_to_index(level) == nearest((grey, grey, grey))
    # The values the old constants rely on.
    assert adapter_mod.rgb_to_index(6) == 2  # 102 -> DARK
    assert adapter_mod.rgb_to_index(9) == 3  # 153 -> GRAY
    assert adapter_mod.rgb_to_index(11) == 4  # 187 -> LIGHT


def test_legacy_int_is_clamped_to_the_grey4_range(adapter_mod):
    assert adapter_mod.rgb_to_index(99) == 5
    assert adapter_mod.rgb_to_index(-3) == 0


def test_mapping_is_cached(adapter_mod):
    first = adapter_mod.rgb_to_index((200, 100, 50))
    assert adapter_mod.rgb_to_index((200, 100, 50)) == first


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
