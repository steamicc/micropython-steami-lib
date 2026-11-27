"""Stub for the MicroPython framebuf module.

Mirrors extmod/modframebuf.c of MicroPython for the formats the STeaMi
drivers use: the pixel layout of GS4_HMSB, MONO_HLSB and RGB565 (native
little-endian words, as on the STM32), and the clipping of pixel, fill_rect,
rect, line, text, blit (with key and palette) and scroll. text() draws the
real 8x8 petme128 font, so tests can compare pixels.
"""

from tests.fake_machine.font_petme128 import FONT_PETME128_8X8

RGB565 = 1
GS4_HMSB = 2
MONO_HLSB = 3

_UINT32 = 0xFFFFFFFF


class FrameBuffer:
    """FrameBuffer stub with the semantics of the MicroPython C module."""

    def __init__(self, buffer, width, height, fmt, stride=None):
        if stride is None:
            stride = width
        if width < 1 or height < 1 or stride < width:
            raise ValueError
        width_required = width
        if fmt == MONO_HLSB:
            stride = (stride + 7) & ~7
            width_required = (width + 7) & ~7
            bpp = 1
        elif fmt == GS4_HMSB:
            stride = (stride + 1) & ~1
            width_required = (width + 1) & ~1
            bpp = 4
        elif fmt == RGB565:
            bpp = 16
        else:
            raise ValueError("invalid format")
        strides_required = height - 1
        needed = (strides_required * stride + width_required) * bpp // 8
        if needed > len(buffer):
            raise ValueError
        self.buffer = buffer
        self.width = width
        self.height = height
        self.stride = stride
        self.format = fmt

    # ----- per-format pixel access (coordinates already in range) -----

    def _set(self, x, y, col):
        buf = self.buffer
        if self.format == GS4_HMSB:
            i = (x + y * self.stride) >> 1
            if x % 2:
                buf[i] = (col & 0x0F) | (buf[i] & 0xF0)
            else:
                buf[i] = ((col << 4) & 0xF0) | (buf[i] & 0x0F)
        elif self.format == MONO_HLSB:
            i = (x + y * self.stride) >> 3
            offset = 7 - (x & 0x07)
            buf[i] = (buf[i] & ~(1 << offset) & 0xFF) | ((col != 0) << offset)
        else:
            i = (x + y * self.stride) * 2
            buf[i] = col & 0xFF
            buf[i + 1] = (col >> 8) & 0xFF

    def _get(self, x, y):
        buf = self.buffer
        if self.format == GS4_HMSB:
            byte = buf[(x + y * self.stride) >> 1]
            return byte & 0x0F if x % 2 else byte >> 4
        if self.format == MONO_HLSB:
            byte = buf[(x + y * self.stride) >> 3]
            return (byte >> (7 - (x & 0x07))) & 0x01
        i = (x + y * self.stride) * 2
        return buf[i] | (buf[i + 1] << 8)

    def _inside(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    # ----- FrameBuffer methods -----

    def fill(self, col):
        for y in range(self.height):
            for x in range(self.width):
                self._set(x, y, col)

    def fill_rect(self, x, y, w, h, col):
        if h < 1 or w < 1 or x + w <= 0 or y + h <= 0 or y >= self.height or x >= self.width:
            return
        xend = min(self.width, x + w)
        yend = min(self.height, y + h)
        x = max(x, 0)
        y = max(y, 0)
        for yy in range(y, yend):
            for xx in range(x, xend):
                self._set(xx, yy, col)

    def pixel(self, x, y, col=None):
        if not self._inside(x, y):
            return None
        if col is None:
            return self._get(x, y)
        self._set(x, y, col)
        return None

    def hline(self, x, y, w, col):
        self.fill_rect(x, y, w, 1, col)

    def vline(self, x, y, h, col):
        self.fill_rect(x, y, 1, h, col)

    def rect(self, x, y, w, h, col, fill=False):
        if fill:
            self.fill_rect(x, y, w, h, col)
            return
        self.fill_rect(x, y, w, 1, col)
        self.fill_rect(x, y + h - 1, w, 1, col)
        self.fill_rect(x, y, 1, h, col)
        self.fill_rect(x + w - 1, y, 1, h, col)

    def line(self, x1, y1, x2, y2, col):
        dx = x2 - x1
        if dx > 0:
            sx = 1
        else:
            dx = -dx
            sx = -1
        dy = y2 - y1
        if dy > 0:
            sy = 1
        else:
            dy = -dy
            sy = -1
        steep = dy > dx
        if steep:
            x1, y1 = y1, x1
            dx, dy = dy, dx
            sx, sy = sy, sx
        e = 2 * dy - dx
        for _ in range(dx):
            px, py = (y1, x1) if steep else (x1, y1)
            if self._inside(px, py):
                self._set(px, py, col)
            while e >= 0:
                y1 += sy
                e -= 2 * dx
            x1 += sx
            e += 2 * dy
        if self._inside(x2, y2):
            self._set(x2, y2, col)

    def blit(self, fbuf, x, y, key=-1, palette=None):
        source = _as_framebuffer(fbuf)
        pal = None if palette is None else _as_framebuffer(palette)
        if x >= self.width or y >= self.height or -x >= source.width or -y >= source.height:
            return
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = max(0, -x)
        y1 = max(0, -y)
        x0end = min(self.width, x + source.width)
        y0end = min(self.height, y + source.height)
        key &= _UINT32
        while y0 < y0end:
            cx1 = x1
            for cx0 in range(x0, x0end):
                col = source._get(cx1, y1)
                if pal is not None:
                    col = pal._get(col, 0)
                if col != key:
                    self._set(cx0, y0, col)
                cx1 += 1
            y0 += 1
            y1 += 1

    def scroll(self, xstep, ystep):
        if xstep < 0:
            if -xstep >= self.width:
                return
            sx, xend, dx = 0, self.width + xstep, 1
        else:
            if xstep >= self.width:
                return
            sx, xend, dx = self.width - 1, xstep - 1, -1
        if ystep < 0:
            if -ystep >= self.height:
                return
            y, yend, dy = 0, self.height + ystep, 1
        else:
            if ystep >= self.height:
                return
            y, yend, dy = self.height - 1, ystep - 1, -1
        while y != yend:
            x = sx
            while x != xend:
                self._set(x, y, self._get(x - xstep, y - ystep))
                x += dx
            y += dy

    def text(self, string, x, y, col=1):
        x0 = x
        for chr_code in string.encode("utf-8"):
            code = chr_code if 32 <= chr_code <= 127 else 127
            base = (code - 32) * 8
            for j in range(8):
                if 0 <= x0 < self.width:
                    vline_data = FONT_PETME128_8X8[base + j]
                    yy = y
                    while vline_data:
                        if vline_data & 1 and 0 <= yy < self.height:
                            self._set(x0, yy, col)
                        vline_data >>= 1
                        yy += 1
                x0 += 1


def _as_framebuffer(obj):
    """Return obj, or a read-only FrameBuffer from (buffer, w, h, fmt[, stride])."""
    if isinstance(obj, FrameBuffer):
        return obj
    if not 4 <= len(obj) <= 5:
        raise ValueError
    return FrameBuffer(*obj)
