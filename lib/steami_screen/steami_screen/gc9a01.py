"""
GC9A01 display wrapper — converts RGB colors to RGB565.

Wraps the raw GC9A01 driver so that steami_screen can pass RGB tuples
while the hardware receives 16-bit RGB565 values.

Usage on the STeaMi board:
    import gc9a01
    from steami_gc9a01 import GC9A01Display
    raw = gc9a01.GC9A01(spi, dc, cs, rst, ...)
    display = GC9A01Display(raw)

This file has'nt been tested on actual hardware yet
"""

from steami_screen.colors import rgb_to_rgb565


class GC9A01Display:
    """Thin wrapper around a GC9A01 driver that accepts RGB colors."""

    def __init__(self, raw, width=240, height=240):
        self._raw = raw
        self.width = width
        self.height = height

    def fill(self, color):
        self._raw.fill(rgb_to_rgb565(color))

    def pixel(self, x, y, color):
        self._raw.pixel(x, y, rgb_to_rgb565(color))

    def text(self, string, x, y, color):
        self._raw.text(string, x, y, rgb_to_rgb565(color))

    def line(self, x1, y1, x2, y2, color):
        self._raw.line(x1, y1, x2, y2, rgb_to_rgb565(color))

    def fill_rect(self, x, y, w, h, color):
        self._raw.fill_rect(x, y, w, h, rgb_to_rgb565(color))

    def rect(self, x, y, w, h, color):
        self._raw.rect(x, y, w, h, rgb_to_rgb565(color))

    def show(self):
        self._raw.show()
