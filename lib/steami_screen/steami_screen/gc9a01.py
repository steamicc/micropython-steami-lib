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


class GC9A01Display:
    """Thin wrapper around a GC9A01 driver that accepts RGB colors."""

    def __init__(self, raw):
        self._raw = raw
        self.width = getattr(raw, "width", 240)
        self.height = getattr(raw, "height", 240)
        # Resolve fill_rect dispatch once at init (avoids repeated hasattr)
        if hasattr(raw, "fill_rect"):
            self._fill_rect_raw = raw.fill_rect
        else:
            self._fill_rect_raw = raw.framebuf.fill_rect
        # 2x1 GS4_HMSB palette of draw_glyphs, made on its first native blit.
        self._pal = None

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

    def draw_glyphs(self, fc, glyphs, n, bold, color):
        """Draw Spleen glyphs of face fc, each (offset, x, y), at replication n.

        Only the glyph's set bits are painted, whatever the colour (BLACK
        included). At n = 1 each glyph is blitted through a 2x1 palette
        (set bit -> c, clear bit -> b != c) with key b; bold blits it again
        one pixel right. At n >= 2 each run of set bits is one fill_rect.
        The colour is looked up once per call.
        """
        c = rgb_to_index(color)
        if n > 1:
            fonts.draw_runs(self._fill_rect_raw, fc, glyphs, n, bold, c)
            return
        import framebuf

        b = 1 if c == 0 else 0
        pal = self._pal
        if pal is None:
            self._pal_buf = bytearray(1)
            pal = self._pal = framebuf.FrameBuffer(self._pal_buf, 2, 1, framebuf.GS4_HMSB)
        self._pal_buf[0] = (b << 4) | c
        raw = self._raw
        blit = raw.blit if hasattr(raw, "blit") else raw.framebuf.blit
        mono = framebuf.MONO_HLSB
        w, h = fc[0], fc[1]
        size = h * ((w + 7) // 8)
        mv = memoryview(fc[4])
        for o, x, y in glyphs:
            src = (mv[o : o + size], w, h, mono)
            blit(src, x, y, b, pal)
            if bold:
                blit(src, x + 1, y, b, pal)
