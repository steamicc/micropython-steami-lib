from time import sleep_ms

import framebuf
import micropython

from gc9a01.const import (
    BAUDRATE,
    CASET,
    DISPOFF,
    DISPON,
    DISPON_DELAY_MS,
    HEIGHT,
    INIT_SEQUENCE,
    PALETTE_RGB565,
    RAMWR,
    RASET,
    RESET_DELAY_MS,
    RESET_PULSE_MS,
    SLEEP_DELAY_MS,
    SLPIN,
    SLPOUT,
    STRIP_ROWS,
    SWRESET,
    WIDTH,
)


@micropython.viper
def _to_rgb565(
    frame: ptr8,  # noqa: F821 (a viper type, resolved by the board compiler)
    start: int,
    rows: int,
    width: int,
    palette: ptr16,  # noqa: F821
    strip: ptr16,  # noqa: F821
):
    """Convert rows of a GS4_HMSB frame to RGB565 through the palette.

    frame has (width + 1) // 2 bytes per row, even x in the high nibble;
    the rows converted start at byte start. palette holds the 16 RGB565
    words as an RGB565 FrameBuffer stores them, so each pixel's two bytes
    are copied as they are and the strip comes out in panel order, as the
    palette blit gave. An odd width's last byte holds one pixel: its low
    nibble is padding and gives no pixel. rows * width words are written
    from the start of strip: viper has no bounds check, so the caller
    keeps rows within the strip and the frame.
    """
    pairs = width >> 1
    stride = (width + 1) >> 1
    j = 0
    r = 0
    while r < rows:
        for k in range(start, start + pairs):
            b = frame[k]
            strip[j] = palette[b >> 4]
            strip[j + 1] = palette[b & 15]
            j += 2
        if width & 1:
            strip[j] = palette[frame[start + pairs] >> 4]
            j += 1
        start += stride
        r += 1


class GC9A01(object):
    """GC9A01 round colour TFT on SPI, with a 16-colour frame.

    The frame is a GS4_HMSB FrameBuffer: each pixel is an index into
    PALETTE (const.py). show() converts it to RGB565 a few rows at a time,
    through a small reused strip buffer, so a full RGB565 frame never sits
    in RAM. Creating the object touches no pin and no bus: call init().
    """

    def __init__(self, spi, dc, cs, rst=None, width=WIDTH, height=HEIGHT):
        self.spi = spi
        self.dc = dc
        self.cs = cs
        self.rst = rst
        self.width = width
        self.height = height
        self.buffer = bytearray((width + 1) // 2 * height)
        self.framebuf = framebuf.FrameBuffer(self.buffer, width, height, framebuf.GS4_HMSB)
        self._rows = min(STRIP_ROWS, height)
        self._strip = bytearray(width * 2 * self._rows)
        # The 16 RGB565 words of the palette, stored by an RGB565 FrameBuffer
        # (native little-endian words): the bytes the panel expects.
        self._palette = bytearray(32)
        palette = framebuf.FrameBuffer(self._palette, 16, 1, framebuf.RGB565)
        for i, word in enumerate(PALETTE_RGB565):
            palette.pixel(i, 0, word)
        self._cmd = bytearray(1)

    # ----- bus -----

    def _begin(self):
        self.spi.init(baudrate=BAUDRATE, polarity=0, phase=0)

    def _write(self, cmd, data=None):
        # CS must already be low: D/C low for the command, high for its data.
        self.dc.value(0)
        self._cmd[0] = cmd
        self.spi.write(self._cmd)
        if data:
            self.dc.value(1)
            self.spi.write(data)

    def _command(self, cmd, data=None):
        self.cs.value(0)
        self._write(cmd, data)
        self.cs.value(1)

    def reset(self):
        """Hardware reset: pulse the rst pin. ValueError without one.

        Without an rst pin, soft_reset() resets the panel instead. Either
        leaves it asleep with its default registers: call init() again.
        """
        rst = self.rst
        if rst is None:
            raise ValueError("no rst pin: use soft_reset()")
        rst.init(rst.OUT, value=1)
        sleep_ms(RESET_PULSE_MS)
        rst.value(0)
        sleep_ms(RESET_PULSE_MS)
        rst.value(1)
        sleep_ms(RESET_DELAY_MS)

    def soft_reset(self):
        """Software reset: the SWRESET command, then its 120 ms wait.

        Leaves the panel asleep with its default registers: call init() again.
        """
        self._begin()
        self._command(SWRESET)
        sleep_ms(RESET_DELAY_MS)

    def init(self):
        """Reset and set up the panel, send a cleared frame, then DISPON.

        The reset is reset() with an rst pin, else soft_reset(). The panel
        RAM is cleared before the display turns on, so its power-on content
        never shows.
        """
        self.cs.init(self.cs.OUT, value=1)
        self.dc.init(self.dc.OUT, value=0)
        if self.rst is None:
            self.soft_reset()
        else:
            self._begin()
            self.reset()
        seq = memoryview(INIT_SEQUENCE)
        i = 0
        while i < len(seq):
            n = seq[i + 1]
            self._command(seq[i], seq[i + 2 : i + 2 + n])
            i += 2 + n
        self._command(SLPOUT)
        sleep_ms(SLEEP_DELAY_MS)
        self.fill(0)
        self.show()
        self._command(DISPON)
        sleep_ms(DISPON_DELAY_MS)

    def power_off(self):
        self._begin()
        self._command(DISPOFF)
        self._command(SLPIN)
        # SLPOUT must not follow SLPIN within 120 ms
        sleep_ms(SLEEP_DELAY_MS)

    def power_on(self):
        self._begin()
        self._command(SLPOUT)
        sleep_ms(SLEEP_DELAY_MS)
        self._command(DISPON)

    def show(self):
        """Send the whole frame, converted to RGB565 strip by strip."""
        spi = self.spi
        rows = self._rows
        strip = self._strip
        frame = self.buffer
        palette = self._palette
        width = self.width
        height = self.height
        stride = (width + 1) // 2
        window = bytearray(4)
        self._begin()
        self.cs.value(0)
        # Window 0..width-1 x 0..height-1: start 0, end high byte first.
        window[2] = (self.width - 1) >> 8
        window[3] = (self.width - 1) & 0xFF
        self._write(CASET, window)
        window[2] = (self.height - 1) >> 8
        window[3] = (self.height - 1) & 0xFF
        self._write(RASET, window)
        self._write(RAMWR)
        self.dc.value(1)
        row_bytes = width * 2
        for y in range(0, height, rows):
            # Rows y..y+n-1 of the frame, through the palette, into the
            # strip: its bytes are already in panel order. The last strip
            # may be short (n < rows): only its n rows are converted and sent.
            n = min(rows, height - y)
            _to_rgb565(frame, y * stride, n, width, palette, strip)
            if n < rows:
                spi.write(memoryview(strip)[: n * row_bytes])
            else:
                spi.write(strip)
        self.cs.value(1)

    # ----- drawing (colours are palette indexes 0-15) -----

    def fill(self, i):
        self.framebuf.fill(i)

    def pixel(self, x, y, i=None):
        if i is None:
            return self.framebuf.pixel(x, y)
        self.framebuf.pixel(x, y, i)
        return None

    def fill_rect(self, x, y, w, h, i):
        self.framebuf.fill_rect(x, y, w, h, i)

    def rect(self, x, y, w, h, i):
        self.framebuf.rect(x, y, w, h, i)

    def line(self, x1, y1, x2, y2, i):
        self.framebuf.line(x1, y1, x2, y2, i)

    def text(self, s, x, y, i):
        self.framebuf.text(s, x, y, i)

    def blit(self, fb, x, y, key=-1, palette=None):
        """Copy fb (a FrameBuffer or a (buf, w, h, fmt[, stride]) tuple) at x, y.

        With a palette, each source pixel value is looked up in it first:
        palette is applied before the key test, so a pixel whose mapped
        colour equals key is skipped.
        """
        self.framebuf.blit(fb, x, y, key, palette)
