"""SSD1327 display wrapper — converts RGB colors to 4-bit grayscale.

Wraps the raw SSD1327 driver so that steami_screen can pass RGB tuples
while the hardware receives grayscale values (0-15).

Usage on the STeaMi board:
    import ssd1327
    from steami_screen import SSD1327Display
    raw = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)
    display = SSD1327Display(raw)
"""

import framebuf

from steami_screen.colors import rgb_to_gray4


class SSD1327Display:
    """Thin wrapper around an SSD1327 driver that accepts RGB colors."""

    def __init__(self, raw):
        self._raw = raw
        self.width = getattr(raw, "width", 128)
        self.height = getattr(raw, "height", 128)

    def fill(self, color):
        self._raw.fill(rgb_to_gray4(color))

    def pixel(self, x, y, color):
        self._raw.pixel(x, y, rgb_to_gray4(color))

    def text(self, string, x, y, color):
        self._raw.text(string, x, y, rgb_to_gray4(color))

    def line(self, x1, y1, x2, y2, color):
        self._raw.line(x1, y1, x2, y2, rgb_to_gray4(color))

    def fill_rect(self, x, y, w, h, color):
        gray = rgb_to_gray4(color)
        if hasattr(self._raw, "fill_rect"):
            self._raw.fill_rect(x, y, w, h, gray)
        else:
            self._raw.framebuf.fill_rect(x, y, w, h, gray)

    def rect(self, x, y, w, h, color):
        gray = rgb_to_gray4(color)
        if hasattr(self._raw, "rect"):
            self._raw.rect(x, y, w, h, gray)
        else:
            self._raw.framebuf.rect(x, y, w, h, gray)

    def show(self):
        self._raw.show()

    def draw_scaled_text(self, text, x, y, color, scale):
        """Draw text scaled up using pixel-by-pixel framebuf rendering.

        Renders each character into a temporary 8x8 MONO_HLSB framebuf,
        reads each lit pixel, and draws a scale x scale filled rectangle.
        This produces a true pixel-scale zoom instead of a bold offset effect.
        """

        gray = rgb_to_gray4(color)

        char_buf = bytearray(8)
        fb = framebuf.FrameBuffer(char_buf, 8, 8, framebuf.MONO_HLSB)

        cx = x
        for char in text:
            fb.fill(0)
            fb.text(char, 0, 0, 1)
            for py in range(8):
                for px in range(8):
                    if fb.pixel(px, py):
                        if hasattr(self._raw, "fill_rect"):
                            self._raw.fill_rect(
                                cx + px * scale,
                                y + py * scale,
                                scale,
                                scale,
                                gray,
                            )
                        else:
                            self._raw.framebuf.fill_rect(
                                cx + px * scale,
                                y + py * scale,
                                scale,
                                scale,
                                gray,
                            )
            cx += 8 * scale
