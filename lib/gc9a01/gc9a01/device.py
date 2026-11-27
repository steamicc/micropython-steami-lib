from time import sleep_ms

import framebuf

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
        self._strip_fb = framebuf.FrameBuffer(self._strip, width, self._rows, framebuf.RGB565)
        self._palette = framebuf.FrameBuffer(bytearray(32), 16, 1, framebuf.RGB565)
        for i, word in enumerate(PALETTE_RGB565):
            self._palette.pixel(i, 0, word)
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
        """Hardware reset with the reset pin, or SWRESET without one."""
        if self.rst is None:
            self._command(SWRESET)
        else:
            self.rst.init(self.rst.OUT, value=1)
            sleep_ms(RESET_PULSE_MS)
            self.rst.value(0)
            sleep_ms(RESET_PULSE_MS)
            self.rst.value(1)
        sleep_ms(RESET_DELAY_MS)

    def init(self):
        """Reset and set up the panel, send a cleared frame, then DISPON.

        The panel RAM is cleared before the display turns on, so its
        power-on content never shows.
        """
        self.cs.init(self.cs.OUT, value=1)
        self.dc.init(self.dc.OUT, value=0)
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
        strip_fb = self._strip_fb
        source = self.framebuf
        palette = self._palette
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
        row_bytes = self.width * 2
        for y in range(0, self.height, rows):
            # Rows y..y+rows-1 of the frame, through the palette, into the
            # strip: its bytes are already in panel order.
            strip_fb.blit(source, 0, -y, -1, palette)
            left = self.height - y
            if left < rows:
                spi.write(memoryview(strip)[: left * row_bytes])
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

    def blit(self, fb, x, y, key=-1):
        self.framebuf.blit(fb, x, y, key)
