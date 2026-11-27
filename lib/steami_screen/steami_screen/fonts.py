"""Font helpers for the Spleen faces of steami_screen.

Pure Python: this module imports neither framebuf nor spleen at import time.
face() imports steami_screen.spleen on its first call, so the 128 px path
(fold8, DEGREE8, draw_runs) never loads the font tables.

A face is a tuple (w, h, ascent, key, data), as in spleen.py. Glyph rows run
top to bottom, (w + 7) // 8 bytes per row, MSB = column 0. key is None for
a full set (codes 32..159) or the string of the characters a value set holds.
"""

# Ink of a text: the face ladder and the advance depend on it.
TEXT = 0
LABEL = 1
VALUE = 2

# Copy of spleen.EXTRA (codes 127..159), so the 128 path never imports spleen.
EXTRA = "°ÀÂÄÇÈÉÊËÎÏÔÖÙÛÜàâäçèéêëîïôöùûüÿŸ"

# spleen.FOLD with '°' mapped to "\x7f": the 128 px text folds each character
# of EXTRA to this one ASCII byte, and "\x7f" stands for the degree sign.
FOLD8 = "\x7fAAACEEEEIIOOUUUaaaceeeeiioouuuyY"

# The 8x8 degree sign (Arduino SteamiFont.cpp glyph 127), as a face tuple.
DEGREE8 = (8, 8, 0, None, b"\x30\x48\x48\x30\x00\x00\x00\x00")

_sp = None  # steami_screen.spleen, imported by the first face() call
_rows = {}  # glyph row masks, keyed by (face height << 16) | offset


def code(ch):
    """Font code of a character: ASCII 32..126, EXTRA 127..159, else '?'."""
    o = ord(ch)
    if 32 <= o <= 126:
        return o
    if o > 126:
        i = EXTRA.find(ch)
        if i >= 0:
            return 127 + i
    return 63


def fold8(s):
    """s with each character of EXTRA folded to its FOLD8 byte.

    Every other character (ASCII, control characters, "\\x7f", non-ASCII
    outside EXTRA) is left as it is, for framebuf to draw as before.
    """
    for ch in s:
        if ord(ch) > 126:
            break
    else:
        return s
    out = []
    for ch in s:
        if ord(ch) > 126:
            i = EXTRA.find(ch)
            if i >= 0:
                ch = FOLD8[i]
        out.append(ch)
    return "".join(out)


def face(s, ink, f):
    """(face, n) that draws s with ink at glyph factor f, or None.

    LABEL is the 6x12 face whatever f. A VALUE text made only of value
    characters ("" included) takes 16x32 (f % 4 == 0), 12x24 (f % 3 == 0)
    or 8x16 (f even). Any other text takes 8x16 when f is even. n is the
    replication of the face.
    """
    global _sp
    sp = _sp
    if sp is None:
        from steami_screen import spleen as sp

        _sp = sp
    if ink == LABEL:
        return sp.F6X12, 1
    if f < 1:
        return None
    if ink == VALUE:
        key = sp.VALUE_KEY
        for ch in s:
            if ch not in key:
                break
        else:
            if f % 4 == 0:
                return sp.F16X32, f // 4
            if f % 3 == 0:
                return sp.F12X24, f // 3
    if f % 2 == 0:
        return sp.F8X16, f // 2
    return None


def offset(fc, ch):
    """Byte offset of the glyph of ch in fc's data.

    For a value set, ch must be one of its key characters.
    """
    key = fc[3]
    i = code(ch) - 32 if key is None else key.find(ch)
    return i * fc[1] * ((fc[0] + 7) // 8)


def advance(ink, f):
    """Pen advance of one character on 240: 6 for LABEL, else 4f."""
    return 6 if ink == LABEL else 4 * f


def widths(s, ink, f):
    """Prefix widths of s: item i is the width of s's first i + 1 characters.

    For VALUE, '.' and ':' advance half.
    """
    a = advance(ink, f)
    narrow = a // 2 if ink == VALUE else a
    x = 0
    out = []
    for ch in s:
        x += narrow if ch in ".:" else a
        out.append(x)
    return out


def width(s, n, ink, f):
    """Width of the first n characters of s."""
    a = advance(ink, f)
    narrow = a // 2 if ink == VALUE else a
    x = 0
    for i, ch in enumerate(s):
        if i >= n:
            break
        x += narrow if ch in ".:" else a
    return x


def masks(fc, s):
    """Prefix ink masks of s in face fc: bit r is set when a glyph inks row r."""
    h, data = fc[1], fc[4]
    bpr = (fc[0] + 7) // 8
    hk = h << 16
    rows = _rows
    m = 0
    out = []
    for ch in s:
        o = offset(fc, ch)
        k = hk | o
        g = rows.get(k)
        if g is None:
            g = 0
            i = o
            for r in range(h):
                for j in range(bpr):
                    if data[i + j]:
                        g |= 1 << r
                        break
                i += bpr
            rows[k] = g
        m |= g
        out.append(m)
    return out


def ink_rows(m):
    """(lowest, highest) set bit of the mask m, which must not be 0."""
    a = 0
    while not m >> a & 1:
        a += 1
    b = a
    while m >> (b + 1):
        b += 1
    return a, b


def draw_runs(fr, fc, glyphs, n, bold, c):
    """Draw glyphs of fc at replication n with one fr(x, y, w, h, c) per run.

    glyphs is an iterable of (offset, x, y). A run is a row's span of set
    bits; with bold, each run is one column wider.
    """
    w, h, data = fc[0], fc[1], fc[4]
    bpr = (w + 7) // 8
    top = 1 << (8 * bpr - 1)
    for o, gx, gy in glyphs:
        for r in range(h):
            i = o + r * bpr
            v = data[i] if bpr == 1 else (data[i] << 8) | data[i + 1]
            col, bit = 0, top
            while v:  # stops as soon as no set bit is left
                if v & bit:
                    a = col
                    while v & bit:
                        v &= ~bit
                        bit >>= 1
                        col += 1
                    fr(gx + a * n, gy + r * n, (col - a + bold) * n, n, c)
                else:
                    bit >>= 1
                    col += 1
