"""GC9A01 display wrapper: maps RGB colours to the driver's 16-colour palette.

Wraps the raw GC9A01 driver so that steami_screen can pass RGB tuples while
the driver frame holds palette indexes (0-15).

Usage on the STeaMi board:
    import gc9a01
    from steami_screen import GC9A01Display
    raw = gc9a01.GC9A01(spi, dc, cs, rst)
    raw.init()
    display = GC9A01Display(raw)
"""

import micropython

from steami_screen import fonts

# Same entries and order as gc9a01.const.PALETTE (index: RGB).
_PALETTE = (
    (0, 0, 0),  # 0 BLACK
    (51, 51, 51),  # 1 GRID_DARK
    (102, 102, 102),  # 2 DARK
    (153, 153, 153),  # 3 GRAY
    (187, 187, 187),  # 4 LIGHT
    (255, 255, 255),  # 5 WHITE
    (119, 255, 119),  # 6 GREEN
    (255, 85, 85),  # 7 RED
    (85, 85, 255),  # 8 BLUE
    (255, 255, 85),  # 9 YELLOW
    (85, 255, 255),  # 10 CYAN
    (255, 85, 255),  # 11 MAGENTA
    (255, 165, 0),  # 12 ORANGE
    (0, 128, 0),  # 13 DARK_GREEN
    (128, 0, 0),  # 14 DARK_RED
    (0, 0, 128),  # 15 DARK_BLUE
)

# Bounded: a program sweeping gradients must not fill the heap.
_CACHE_MAX = 64
_cache = {}


def rgb_to_index(color):
    """Return the palette index (0-15) nearest to a colour.

    The nearest entry is the one with the smallest squared RGB distance.
    A legacy int is a grey4 level (as in colors.py): it is clamped to 0-15,
    expanded to the grey level * 17 (R = G = B), then mapped the same way,
    except that a non-zero level, visible on the SSD1327, is never BLACK.
    """
    level = 0
    if isinstance(color, int):
        level = max(0, min(15, color))
        color = (level * 17,) * 3
    else:
        color = tuple(color)
    index = _cache.get(color)
    if index is None:
        r, g, b = color
        best = 0
        best_dist = 3 * 255 * 255 + 1
        for i, (pr, pg, pb) in enumerate(_PALETTE):
            dist = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
            if dist < best_dist:
                best = i
                best_dist = dist
        if len(_cache) >= _CACHE_MAX:
            _cache.clear()
        index = _cache[color] = best
    if level and not index:
        index = 1  # GRID_DARK
    return index


@micropython.viper
def _write_glyph(
    frame: ptr8,  # noqa: F821 (a viper type, resolved by the board compiler)
    dims: int,
    src: ptr8,  # noqa: F821
    o: int,
    bpr: int,
    h: int,
    x: int,
    y: int,
    n: int,
    ink: int,
):
    """Write the set bits of one glyph into a GS4_HMSB frame, clipped to it.

    frame is (width + 1) // 2 bytes per row (even x = high nibble), dims is
    (width << 16) | height. The glyph is h rows of bpr bytes at src[o],
    MSB = column 0, drawn at (x, y) with each font pixel an n x n block.
    bpr is 1 or 2 (faces up to 16 px wide): draw_glyphs checks the width and
    that the glyph lies wholly in src before the call.
    ink is the palette index (0-15), plus 16 for bold: each row is ORed with
    itself one column right, so a run gains one column, as the second blit
    at x + 1 (n = 1) or fonts.draw_runs (n >= 2) gave. Clear bits leave the
    frame as it is. Every write is clipped to 0 <= x < width,
    0 <= y < height: viper has no bounds check.
    """
    fw = dims >> 16
    fh = dims & 0xFFFF
    stride = (fw + 1) >> 1
    c = ink & 15
    hi = c << 4
    cc = hi | c
    # Each row is shifted left one bit (v << 1 below) so that bold can ink the
    # column just past the last one: bit top is font column 0.
    top = 1 << (bpr << 3)
    r = 0
    py = y
    while r < h:
        if py >= fh:
            break
        # Font row r covers pixel rows y0 .. y1 - 1 once clipped.
        y0 = 0 if py < 0 else py
        y1 = fh if py + n > fh else py + n
        if y0 < y1:
            i = o + r * bpr
            v = src[i]
            if bpr == 2:
                v = (v << 8) | src[i + 1]
            v = v << 1
            if ink & 16:  # bold
                v = v | (v >> 1)
            bit = top
            col = 0
            while v:
                if v & bit:
                    a = col
                    while v & bit:
                        v = v ^ bit
                        bit = bit >> 1
                        col += 1
                    # The run is font columns a .. col - 1: pixels x0 .. x1 - 1.
                    x0 = x + a * n
                    x1 = x + col * n
                    x0 = 0 if x0 < 0 else x0
                    x1 = fw if x1 > fw else x1
                    if x0 < x1:
                        row = y0 * stride + (x0 >> 1)
                        q = y0
                        while q < y1:
                            p = row
                            px = x0
                            if px & 1:
                                frame[p] = (frame[p] & 0xF0) | c
                                p += 1
                                px += 1
                            while px + 1 < x1:
                                frame[p] = cc
                                p += 1
                                px += 2
                            if px < x1:
                                frame[p] = (frame[p] & 0x0F) | hi
                            row += stride
                            q += 1
                else:
                    bit = bit >> 1
                    col += 1
        r += 1
        py += n


class GC9A01Display:
    """Thin wrapper around a GC9A01 driver that accepts RGB colors."""

    # A colour panel: Screen keeps every widget colour as given.
    is_color = True

    def __init__(self, raw):
        self._raw = raw
        self.width = getattr(raw, "width", 240)
        self.height = getattr(raw, "height", 240)
        # Resolve fill_rect dispatch once at init (avoids repeated hasattr)
        if hasattr(raw, "fill_rect"):
            self._fill_rect_raw = raw.fill_rect
        else:
            self._fill_rect_raw = raw.framebuf.fill_rect
        # draw_glyphs state, resolved on its first call: the driver's GS4_HMSB
        # frame (False when the raw has none) and its (width << 16) | height.
        self._frame = None
        self._dims = 0
        # Without a frame, made on the first native blit: the 2x1 GS4_HMSB
        # palette, the framebuf module, the blit (the C FrameBuffer.blit when
        # the driver has a framebuf) and the glyph data memoryviews.
        self._pal = None
        self._fbm = None
        self._blit = None
        self._mvs = {}

    def fill(self, color):
        self._raw.fill(rgb_to_index(color))

    def pixel(self, x, y, color):
        self._raw.pixel(x, y, rgb_to_index(color))

    def text(self, string, x, y, color):
        self._raw.text(string, x, y, rgb_to_index(color))

    def line(self, x1, y1, x2, y2, color):
        self._raw.line(x1, y1, x2, y2, rgb_to_index(color))

    def fill_rect(self, x, y, w, h, color):
        self._fill_rect_raw(x, y, w, h, rgb_to_index(color))

    def native_fill(self, color):
        """(fill_rect, value): the raw driver's fill_rect and the palette index of color.

        For many rects of one colour (the gauge arc spans): fill_rect(x, y,
        w, h, value) draws on the driver with no conversion per call.
        """
        return self._fill_rect_raw, rgb_to_index(color)

    def rect(self, x, y, w, h, color):
        index = rgb_to_index(color)
        if hasattr(self._raw, "rect"):
            self._raw.rect(x, y, w, h, index)
        else:
            self._raw.framebuf.rect(x, y, w, h, index)

    def show(self):
        self._raw.show()

    def draw_scaled_text(self, text, x, y, color, scale):
        """Draw text with true pixel-scale zoom.

        Each character is rendered into a temporary 8x8 MONO_HLSB framebuf,
        then each lit pixel is expanded into a scale x scale filled rectangle
        on the display. The framebuf import is deferred to avoid breaking
        imports in CPython environments where framebuf is not available.
        """
        import framebuf

        index = rgb_to_index(color)
        blit = self._fill_rect_raw

        char_buf = bytearray(8)
        fb = framebuf.FrameBuffer(char_buf, 8, 8, framebuf.MONO_HLSB)

        cx = x
        for char in text:
            fb.fill(0)
            fb.text(char, 0, 0, 1)
            for py in range(8):
                for px in range(8):
                    if fb.pixel(px, py):
                        blit(cx + px * scale, y + py * scale, scale, scale, index)
            cx += 8 * scale

    def _gs4_frame(self):
        """The raw's GS4_HMSB frame buffer for _write_glyph, or False.

        The buffer must hold ((width + 1) // 2) * height bytes: _write_glyph
        stays inside that size, so a smaller one is never handed to it. The
        width stays below 32768: dims is a signed 32-bit viper int on the
        board, and a larger width would make dims >> 16 negative there.
        """
        raw = self._raw
        buf = getattr(raw, "buffer", None)
        w = getattr(raw, "width", None)
        h = getattr(raw, "height", None)
        if buf is None or w is None or h is None or not 0 < w < 32768 or not 0 < h < 65536:
            return False
        if len(buf) < (w + 1) // 2 * h:
            return False
        self._dims = (w << 16) | h
        return buf

    def draw_glyphs(self, fc, glyphs, n, bold, color):
        """Draw Spleen glyphs of face fc, each (offset, x, y), at replication n.

        Only the glyph's set bits are painted, whatever the colour (BLACK
        included). On the gc9a01 driver, whose GS4_HMSB frame is raw.buffer,
        _write_glyph (viper) writes each glyph of a face up to 16 px wide
        into the frame, clipped, at any n and bold: the same pixels as the
        paths below, in one call. A glyph offset outside the face data
        raises ValueError there, since viper reads it unchecked.
        Other raws: at n = 1 each glyph is blitted through a 2x1 palette
        (set bit -> c, clear bit -> b != c) with key b; bold blits it again
        one pixel right. At n >= 2 each run of set bits is one fill_rect.
        The colour is looked up once per call; the frame, the framebuf
        module, the blit and each face's memoryview are resolved once per
        display.
        """
        c = rgb_to_index(color)
        frame = self._frame
        if frame is None:
            frame = self._frame = self._gs4_frame()
        if frame and fc[0] <= 16:
            write = _write_glyph
            dims = self._dims
            data, bpr, h = fc[4], (fc[0] + 7) // 8, fc[1]
            ink = c | 16 if bold else c
            # _write_glyph reads src[o ...] unchecked: each glyph must lie
            # wholly in the face data.
            last = len(data) - h * bpr
            for o, x, y in glyphs:
                if not 0 <= o <= last:
                    raise ValueError("glyph offset outside the face")
                write(frame, dims, data, o, bpr, h, x, y, n, ink)
            return
        if n > 1:
            fonts.draw_runs(self._fill_rect_raw, fc, glyphs, n, bold, c)
            return
        fbm = self._fbm
        if fbm is None:
            import framebuf

            fbm = self._fbm = framebuf
            self._pal_buf = bytearray(1)
            self._pal = framebuf.FrameBuffer(self._pal_buf, 2, 1, framebuf.GS4_HMSB)
            raw = self._raw
            self._blit = raw.framebuf.blit if hasattr(raw, "framebuf") else raw.blit
        b = 1 if c == 0 else 0
        pal = self._pal
        self._pal_buf[0] = (b << 4) | c
        blit = self._blit
        mono = fbm.MONO_HLSB
        w, h = fc[0], fc[1]
        size = h * ((w + 7) // 8)
        data = fc[4]
        mvs = self._mvs
        entry = mvs.get(id(data))
        if entry is None or entry[0] is not data:
            entry = mvs[id(data)] = (data, memoryview(data))
        mv = entry[1]
        for o, x, y in glyphs:
            src = (mv[o : o + size], w, h, mono)
            blit(src, x, y, b, pal)
            if bold:
                blit(src, x + 1, y, b, pal)
