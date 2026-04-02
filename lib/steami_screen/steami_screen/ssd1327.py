"""
SSD1327 display wrapper — converts RGB colors to 4-bit grayscale.

Wraps the raw SSD1327 driver so that steami_screen can pass RGB tuples
while the hardware receives grayscale values (0-15).

Usage on the STeaMi board:
    import ssd1327
    from steami_ssd1327 import SSD1327Display
    raw = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)
    display = SSD1327Display(raw)
"""

from steami_screen.colors import rgb_to_gray4


class SSD1327Display:
    """Thin wrapper around an SSD1327 driver that accepts RGB colors."""

    def __init__(self, raw):
        self._raw = raw
        self.width = getattr(raw, 'width', 128)
        self.height = getattr(raw, 'height', 128)

    def fill(self, color):
        self._raw.fill(rgb_to_gray4(color))

    def pixel(self, x, y, color):
        self._raw.pixel(x, y, rgb_to_gray4(color))

    def text(self, string, x, y, color):
        self._raw.text(string, x, y, rgb_to_gray4(color))

    def line(self, x1, y1, x2, y2, color):
        self._raw.line(x1, y1, x2, y2, rgb_to_gray4(color))

    def fill_rect(self, x, y, w, h, color):
        self._raw.fill_rect(x, y, w, h, rgb_to_gray4(color))

    def rect(self, x, y, w, h, color):
        self._raw.rect(x, y, w, h, rgb_to_gray4(color))

    def show(self):
        self._raw.show()
