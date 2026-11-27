"""Tests of the framebuf stub against MicroPython extmod/modframebuf.c.

The stub stands for the C module on CPython: these tests pin the pixel
layout of each format and the clipping rules, so driver tests that compare
real pixels check what the board would draw.
"""

import pytest

from tests.fake_machine import framebuf_stub as framebuf
from tests.fake_machine.font_petme128 import FONT_PETME128_8X8


def _fb(fmt, width, height):
    size = {
        framebuf.GS4_HMSB: ((width + 1) // 2) * height,
        framebuf.MONO_HLSB: ((width + 7) // 8) * height,
        framebuf.RGB565: width * height * 2,
    }[fmt]
    buf = bytearray(size)
    return framebuf.FrameBuffer(buf, width, height, fmt), buf


def _lit(fb):
    return {(x, y) for y in range(fb.height) for x in range(fb.width) if fb.pixel(x, y)}


# ----- Pixel layout -----


def test_format_constants_match_micropython():
    assert framebuf.RGB565 == 1
    assert framebuf.GS4_HMSB == 2
    assert framebuf.MONO_HLSB == 3


def test_gs4_hmsb_even_pixel_is_high_nibble():
    fb, buf = _fb(framebuf.GS4_HMSB, 4, 2)
    fb.pixel(0, 1, 0xA)
    fb.pixel(1, 1, 0x5)
    assert buf == bytearray([0, 0, 0xA5, 0])
    assert fb.pixel(0, 1) == 0xA
    assert fb.pixel(1, 1) == 0x5


def test_mono_hlsb_leftmost_pixel_is_msb():
    fb, buf = _fb(framebuf.MONO_HLSB, 16, 2)
    fb.pixel(0, 0, 1)
    fb.pixel(9, 1, 7)  # any non-zero colour lights the pixel
    assert buf == bytearray([0x80, 0, 0, 0x40])
    assert fb.pixel(9, 1) == 1


def test_rgb565_words_are_little_endian():
    fb, buf = _fb(framebuf.RGB565, 2, 1)
    fb.pixel(1, 0, 0x1234)
    assert buf == bytearray([0, 0, 0x34, 0x12])
    assert fb.pixel(1, 0) == 0x1234


def test_buffer_too_small_raises():
    with pytest.raises(ValueError):
        framebuf.FrameBuffer(bytearray(3), 4, 2, framebuf.GS4_HMSB)


def test_pixel_outside_is_ignored():
    fb, buf = _fb(framebuf.GS4_HMSB, 4, 4)
    fb.pixel(-1, 0, 15)
    fb.pixel(4, 0, 15)
    fb.pixel(0, -1, 15)
    fb.pixel(0, 4, 15)
    assert not any(buf)
    assert fb.pixel(-1, 0) is None


# ----- fill_rect, rect, line -----


def test_fill_rect_clips_to_the_buffer():
    fb, _ = _fb(framebuf.GS4_HMSB, 8, 8)
    fb.fill_rect(-2, -2, 4, 4, 3)
    fb.fill_rect(6, 7, 10, 10, 4)
    assert _lit(fb) == {(0, 0), (1, 0), (0, 1), (1, 1), (6, 7), (7, 7)}
    assert fb.pixel(7, 7) == 4


def test_fill_rect_empty_or_outside_draws_nothing():
    fb, buf = _fb(framebuf.GS4_HMSB, 8, 8)
    fb.fill_rect(0, 0, 0, 5, 3)
    fb.fill_rect(-10, 0, 5, 5, 3)
    fb.fill_rect(300, 0, 5, 5, 3)
    assert not any(buf)


def test_rect_draws_the_outline_or_fills():
    fb, _ = _fb(framebuf.GS4_HMSB, 8, 8)
    fb.rect(1, 1, 3, 3, 2)
    assert _lit(fb) == {(x, y) for x in (1, 2, 3) for y in (1, 2, 3)} - {(2, 2)}
    fb.rect(1, 1, 3, 3, 2, True)
    assert (2, 2) in _lit(fb)


def test_fill_uses_the_whole_buffer():
    fb, buf = _fb(framebuf.RGB565, 3, 2)
    fb.fill(0xABCD)
    assert buf == bytearray([0xCD, 0xAB] * 6)


def test_line_follows_micropython_and_clips():
    fb, _ = _fb(framebuf.GS4_HMSB, 8, 8)
    fb.line(0, 0, 3, 1, 1)
    assert _lit(fb) == {(0, 0), (1, 0), (2, 1), (3, 1)}
    fb.fill(0)
    fb.line(-4, 2, 20, 2, 1)
    assert _lit(fb) == {(x, 2) for x in range(8)}


# ----- text -----


def test_text_draws_the_petme128_glyph():
    fb, _ = _fb(framebuf.GS4_HMSB, 16, 8)
    fb.text("A", 0, 0, 5)
    glyph = FONT_PETME128_8X8[(ord("A") - 32) * 8 : (ord("A") - 31) * 8]
    expected = {(x, y) for x in range(8) for y in range(8) if glyph[x] >> y & 1}
    assert _lit(fb) == expected
    assert all(fb.pixel(x, y) == 5 for x, y in expected)


def test_text_clips_and_advances_eight_pixels():
    fb, _ = _fb(framebuf.MONO_HLSB, 8, 8)
    fb.text("AB", -8, 0)  # default colour 1; "A" is off screen, "B" lands at x=0
    glyph = FONT_PETME128_8X8[(ord("B") - 32) * 8 : (ord("B") - 31) * 8]
    assert _lit(fb) == {(x, y) for x in range(8) for y in range(8) if glyph[x] >> y & 1}


def test_text_out_of_font_uses_glyph_127():
    fb, _ = _fb(framebuf.MONO_HLSB, 8, 8)
    fb.text("\x01", 0, 0, 1)
    glyph = FONT_PETME128_8X8[95 * 8 :]
    assert _lit(fb) == {(x, y) for x in range(8) for y in range(8) if glyph[x] >> y & 1}


# ----- blit -----


def test_blit_with_key_skips_matching_pixels():
    src, _ = _fb(framebuf.GS4_HMSB, 2, 1)
    src.pixel(0, 0, 3)
    dst, _ = _fb(framebuf.GS4_HMSB, 8, 8)
    dst.fill(9)
    dst.blit(src, 5, 5, 0)
    assert dst.pixel(5, 5) == 3
    assert dst.pixel(6, 5) == 9


def test_blit_clips_negative_offsets():
    src, _ = _fb(framebuf.GS4_HMSB, 4, 4)
    src.pixel(3, 3, 7)
    src.pixel(1, 1, 6)
    dst, _ = _fb(framebuf.GS4_HMSB, 4, 4)
    dst.blit(src, -2, -2)
    assert dst.pixel(1, 1) == 7
    assert dst.pixel(0, 0) == 0  # (2, 2) of the source is blank
    assert _lit(dst) == {(1, 1)}


def test_blit_with_palette_converts_gs4_to_rgb565():
    src, _ = _fb(framebuf.GS4_HMSB, 4, 2)
    src.pixel(0, 1, 1)
    src.pixel(1, 1, 2)
    palette, _ = _fb(framebuf.RGB565, 16, 1)
    palette.pixel(1, 0, 0x1122)
    palette.pixel(2, 0, 0x3344)
    dst, buf = _fb(framebuf.RGB565, 4, 1)
    dst.blit(src, 0, -1, -1, palette)  # row 1 of the source into row 0
    assert buf == bytearray([0x22, 0x11, 0x44, 0x33, 0, 0, 0, 0])


def test_blit_palette_key_compares_the_converted_colour():
    src, _ = _fb(framebuf.MONO_HLSB, 8, 1)
    src.pixel(0, 0, 1)
    palette, _ = _fb(framebuf.GS4_HMSB, 2, 1)
    palette.pixel(0, 0, 4)
    palette.pixel(1, 0, 11)
    dst, _ = _fb(framebuf.GS4_HMSB, 8, 1)
    dst.blit(src, 0, 0, 4, palette)  # background (palette 4) is the key
    assert dst.pixel(0, 0) == 11
    assert _lit(dst) == {(0, 0)}


def test_blit_accepts_a_tuple_source():
    dst, _ = _fb(framebuf.GS4_HMSB, 4, 1)
    dst.blit((bytes([0x12, 0x30]), 4, 1, framebuf.GS4_HMSB), 0, 0)
    assert [dst.pixel(x, 0) for x in range(4)] == [1, 2, 3, 0]


# ----- scroll -----


def test_scroll_shifts_and_keeps_the_vacated_column():
    fb, _ = _fb(framebuf.GS4_HMSB, 4, 1)
    for x, col in enumerate((1, 2, 3, 4)):
        fb.pixel(x, 0, col)
    fb.scroll(1, 0)
    assert [fb.pixel(x, 0) for x in range(4)] == [1, 1, 2, 3]
