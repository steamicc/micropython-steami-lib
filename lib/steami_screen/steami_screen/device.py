"""
steami_screen — High-level API for the STeaMi round display.

Works with any backend that implements the display interface:
  - SSD1327 (128x128 grayscale OLED)
  - GC9A01  (240x240 RGB TFT)
  - SimBackend (Pillow, for screenshots and validation)

3-level API:
  Level 1 — Widgets:  title(), value(), subtitle(), bar(), gauge(), face(), compass()...
  Level 2 — Cardinal: text("hello", at="NE"), line(...), circle(...)
  Level 3 — Pixels:   pixel(x, y, color) with screen.center, screen.radius

Scaling rule (as the Arduino SteamiScreen): widget layout is written in
128 px units, mapped by u(v) = v * width / 128; glyphs and strokes use the
factor k = (width + 64) // 128, 1 on the 128 px SSD1327 and 2 on the 240 px
GC9A01. When k > 1, widget text is kept inside the round screen: it is
moved or cut to the longest prefix that fits the circle at its inked rows.

Fonts, one per panel: the 128 px panel draws the 8x8 framebuf font, accents
folded to their base letter and '°' drawn as Arduino's 8x8 degree. On the
240 px panel the text is Spleen (steami_screen.spleen, through
steami_screen.fonts), with accents: text(s, at=(x, y)) is Spleen 8x16 x
scale. Strokes still use k. Primitives and text(s, at=(x, y)) take real
pixels.
"""

import math

from steami_screen import fonts
from steami_screen.const import (
    BLACK,
    DARK,
    FACES,
    GRAY,
    GRID_DARK,
    LIGHT,
    STEAMI_CHAR_H,
    STEAMI_CHAR_W,
    STEAMI_DEFAULT_HEIGHT,
    STEAMI_DEFAULT_WIDTH,
    STEAMI_GRAPH_DASH,
    STEAMI_GRAPH_GAP,
    STEAMI_GRAPH_HEIGHT,
    STEAMI_GRAPH_MARGIN,
    STEAMI_GRAPH_VALUE_Y,
    STEAMI_GRAPH_X_OFFSET,
    STEAMI_GRAPH_Y,
    STEAMI_MENU_ROW_CELLS,
    STEAMI_TITLE_CAP_CELLS,
    STEAMI_VALUE_FIT_MARGIN,
    STEAMI_VALUE_SIDE_GAP,
    WHITE,
)
from steami_screen.fonts import LABEL, TEXT, VALUE


def _ray(deg):
    """(cos, sin) of an angle in degrees, in Q14 fixed point."""
    a = math.radians(deg)
    return round(16384 * math.cos(a)), round(16384 * math.sin(a))


class Screen:
    """High-level wrapper around a raw display backend."""

    # Exposed as class attributes for backward compatibility (public API).
    CHAR_W = STEAMI_CHAR_W
    CHAR_H = STEAMI_CHAR_H

    def __init__(self, display, width=None, height=None):
        self._d = display
        self.width = width or getattr(display, "width", STEAMI_DEFAULT_WIDTH)
        self.height = height or getattr(display, "height", STEAMI_DEFAULT_HEIGHT)

    # --- Adaptive properties ---

    @property
    def center(self):
        return (self.width // 2, self.height // 2)

    @property
    def radius(self):
        return min(self.width, self.height) // 2

    @property
    def max_chars(self):
        """Characters of text that fit the width: 16 on 128 px, 30 on 240 px."""
        k = self.k
        return self.width // (8 if k == 1 else 4 * k)

    def text_height(self, scale=1):
        """Cell height of text(s, (x, y), c, scale): 8 x scale on 128, 16 x scale on 240."""
        return (8 if self.k == 1 else 16) * max(scale, 1)

    @property
    def k(self):
        """Glyph and stroke factor: 1 on 128 px, 2 on 240 px."""
        return max(1, (self.width + 64) // 128)

    def u(self, v):
        """Map v, in 128 px units, to real pixels (truncated toward zero)."""
        return int(v * self.width / 128)

    # --- Cardinal position resolver ---

    def _margin_ew(self, f):
        """Side margin of text of glyph factor f: (8f + 4k) * W / 128k."""
        k = self.k
        return (8 * f + 4 * k) * self.width // (128 * k)

    def _at(self, at, tw, f):
        """(x, y) of text tw px wide, glyph factor f, at a cardinal position.

        The N/S row moves down until the text fits the circle, from a floor of
        2 cells + 4 (in 128 px units). When k > 1 it stops at the cap, the row
        of a 13-cell text (wider text is cut there): 13 advances of 8 px, so
        on 240 px the cap row (14) is above the floor (37), where every title
        sits.
        """
        k = self.k
        cx, cy = self.center
        r = self.radius
        h = tw // 2
        if k > 1:
            h = min(h, STEAMI_TITLE_CAP_CELLS * fonts.advance(TEXT, k) // 2)
        if k == 1 and h >= r:
            m = r
        else:
            m = max(
                r - int(math.sqrt(max(0, r * r - h * h))) + 2,
                (16 * f + 4 * k) * self.width // (128 * k),
            )
        x = cx - tw // 2
        y = cy - 4 * f if k == 1 else self.u(64 - 4 * (f // k))
        if at in ("NW", "W", "SW"):
            x = self._margin_ew(f)
        elif at in ("NE", "E", "SE"):
            x = self.width - self._margin_ew(f) - tw
        if at in ("N", "NE", "NW"):
            y = m
        elif at in ("S", "SE", "SW"):
            y = self.height - m - 8 * f
        return x, y

    # --- Round-screen fitting (k > 1) ---

    def _chord(self, top, bottom):
        """(left, right) of the circle on rows top..bottom (the narrower), or None."""
        r = self.radius
        cx, cy = self.center
        h = r
        for y in (top, bottom):
            d = y - cy
            if d * d > r * r:
                return None
            h = min(h, int(math.sqrt(r * r - d * d)))
        return cx - h, cx + h

    def _band(self, m, y, n):
        """Chord at the rows that mask m inks (face replication n, cell top y).

        Font row r covers the panel rows y + r * n .. y + r * n + n - 1. The
        whole panel width when m has no ink.
        """
        if not m:
            return 0, self.width - 1
        a, b = fonts.ink_rows(m)
        return self._chord(y + a * n, y + b * n + n - 1)

    def _fit(self, s, y, ink, f, lo=0, hi=None, shrink=0, pad=0):
        """Longest prefix of s that fits [lo, hi] and the chord at its ink rows.

        The face is judged once on the whole s, and every prefix is measured
        in it. The chord is shrunk by `shrink` at each end. Returns (n, lo,
        hi, fn): the characters kept, the room they fit in and the (face,
        replication) pair, None when s has no face at f.
        """
        if hi is None:
            hi = self.width - 1
        fn = fonts.face(s, ink, f)
        if not fn:
            return 0, lo, hi, None
        pre = fonts.masks(fn[0], s)
        wid = fonts.widths(s, ink, f)
        rep = fn[1]
        n = len(s)
        while n:
            m = pre[n - 1]
            c = self._band(m, y, rep)
            if c:
                left, right = max(c[0] + shrink, lo), min(c[1] - shrink, hi)
                if not m or wid[n - 1] + pad <= right - left + 1:
                    return n, left, right, fn
            n -= 1
        return 0, lo, hi, fn

    def _place(self, s, ax, y, color, ink, f, align, fit):
        """Draw the prefix of s that `fit` (a _fit result) keeps, in its room.

        align: 0 left edge at ax, 1 centred on ax, 2 right edge before ax,
        3 centred in the room. x is clamped into the room. The prefix is drawn
        in the face judged on the whole s. Returns (x, width).
        """
        n, lo, hi, fn = fit
        w = fonts.width(s, n, ink, f)
        if align == 3:
            ax, align = (lo + hi + 1) // 2, 1
        x = max(lo, min(ax - (0, w // 2, w)[align], hi - w + 1))
        if n:
            self._draw(s[:n], x, y, color, ink, f, fn)
        return x, w

    def _put(self, s, ax, y, color, ink, f, align=1, lo=0, hi=None, shrink=0):
        """Draw the longest prefix of s that fits (see _fit and _place)."""
        return self._place(s, ax, y, color, ink, f, align, self._fit(s, y, ink, f, lo, hi, shrink))

    def _tw(self, s, ink, f):
        """Width of text s drawn with ink at glyph factor f."""
        if self.k == 1:
            return len(s) * 8 * f
        return fonts.width(s, len(s), ink, f)

    def _draw(self, s, x, y, color, ink, f, fn=None):
        """Draw s in its Spleen face at (x, y), the top of its cell (k > 1 only).

        fn is the (face, n) pair judged on the whole text by the caller, so a
        cut prefix keeps the face of the whole text; when None it is judged
        on s. Without a face nothing is drawn. VALUE ink draws '.' and ':'
        narrow (shifted left by a quarter cell, half advance) and is bold on
        12x24 and 16x32.
        """
        if fn is None:
            fn = fonts.face(s, ink, f)
        if not fn:
            return
        fc, n = fn
        adv = fonts.advance(ink, f)
        bold = 1 if ink == VALUE and fc[0] >= 12 else 0
        shift = (fc[0] // 4) * n
        value = ink == VALUE
        hk = fc[1] << 16
        cache = fonts._glyphs
        entries = []
        for ch in s:
            e = cache.get(hk | ord(ch))
            if e is None:
                e = fonts.glyph(fc, ch)
            if value and ch in ".:":
                entries.append((e[0], x - shift, y))
                x += adv // 2
            else:
                entries.append((e[0], x, y))
                x += adv
        draw = getattr(self._d, "draw_glyphs", None)
        if draw:
            draw(fc, entries, n, bold, color)
        else:
            fonts.draw_runs(self._fill_rect, fc, entries, n, bold, color)

    # --- Level 1: Widgets ---

    def title(self, text, color=GRAY):
        """Draw title text at the top (N)."""
        self.text(text, "N", color)

    def value(self, val, unit=None, at="CENTER", label=None, color=WHITE, scale=2, y_offset=0):
        """Draw a large value, optionally with unit below and label above."""
        text = str(val)
        if self.k > 1:
            self._value(text, unit, at, label, color, scale, y_offset)
            return
        cx, cy = self.center
        char_w = self.CHAR_W * scale
        char_h = self.CHAR_H * scale
        tw = len(text) * char_w // 2

        if unit:
            gap = char_h // 3
            unit_h = self.CHAR_H
            block_h = char_h + gap + unit_h
            vy = cy - block_h // 2
        else:
            vy = cy - char_h // 2

        if at == "CENTER":
            x = cx - tw // 2
            y = vy + y_offset
        elif at == "W":
            x = self.width // 4 - tw // 2
            y = vy + y_offset
        elif at == "E":
            x = 3 * self.width // 4 - tw // 2
            y = vy + y_offset
        else:
            x, y = self._at(at, len(text) * char_w, scale)

        if label:
            lx = x + tw // 2 - len(label) * self.CHAR_W // 2
            self._text8(label, lx, y - self.CHAR_H - 4, GRAY, 1, "text")

        self._text8(text, x, y, color, scale, None)

        if unit:
            unit_y = y + char_h
            ux = x + tw // 2 - len(unit) * self.CHAR_W // 2
            self._txt(unit, ux, unit_y, LIGHT, 1, "draw_medium_text")

    def _value(self, text, unit, at, label, color, scale, y_offset):
        """value() when k > 1: Arduino's fit of the value, its label and unit.

        The glyph factor goes from scale * k down to k until the value fits
        its region, skipping a factor without a value face; at k the value is
        cut. W and E use the half region of their side, sized for the widest
        of the text and "88.8". The value and its label are fitted once, then
        placed.
        """
        k = self.k
        f = max(scale, 1) * k
        cx, cy = self.center
        w = self.width
        gap = self.u(STEAMI_VALUE_SIDE_GAP)
        side = at in ("W", "E")
        corner = at in ("NE", "NW", "SE", "SW")
        pad = 0 if side or corner else self.u(STEAMI_VALUE_FIT_MARGIN)
        fit = None
        while True:
            if f > k and not fonts.face(text, VALUE, f):
                f -= 1
                continue
            vw = fonts.width(text, len(text), VALUE, f)
            x, y = self._at(at, vw, f)
            if not corner and at not in ("N", "S"):
                block = 8 * f + (8 * f // 3 + 8 * k if unit else 0)
                y = cy + self.u(y_offset) - block // 2
            lo, hi = 0, w - 1
            if side or corner:
                c = self._chord(y, y + 8 * f - 1) or (w, -w)
                lo, hi = c[0] + k, c[1] - k
                if at == "W":
                    hi = cx - gap - 1
                elif at == "E":
                    lo = cx + gap + 1
                # B6: "88.8" (14f) sets the factor of every narrower value at W/E.
                if side:
                    fits = max(vw, fonts.width("88.8", 4, VALUE, f)) <= hi - lo + 1
                else:
                    fits = lo <= x <= hi - vw + 1
            else:
                fit = self._fit(text, y, VALUE, f, lo, hi, 0, pad)
                fits = fit[0] == len(text)
            if fits or f == k:
                break
            f -= 1
        if side or corner:
            fit = self._fit(text, y, VALUE, f, lo, hi, 0, pad)
        if side:
            ax, align = 0, 3
        elif corner:
            ax, align = x, 0
            if at[1] == "E":
                ax, align = x + vw, 2
        else:
            ax, align = cx, 1
        vx, vw = self._place(text, ax, y, color, VALUE, f, align, fit)
        # Label and unit: the chord at their own rows, within the value's half
        # at W and E (centred there), shrunk by k at the sides and corners.
        ax = vx + vw // 2 if corner else cx
        lo, hi = 0, w - 1
        if at == "W":
            hi = cx - gap - 1
        elif at == "E":
            lo = cx + gap + 1
        sh = k if side or corner else 0
        align = 3 if side else 1
        if label:
            # Label 6x12 at top - u(4) - 12 (its cell height is 12 on 240).
            ly, fit = self._label_fit(label, y - self.u(4) - 12, y, lo, hi, sh)
            self._place(label, ax, ly, GRAY, LABEL, k, align, fit)
        if unit:
            self._put(unit, ax, y + 8 * f, LIGHT, TEXT, k, align, lo, hi, sh)

    def _label_fit(self, label, ly, y, lo, hi, sh):
        """(row, fit) of a value label whose cell top is ly, the value top y.

        Near the top its rows can leave the circle: when no character fits on
        ly, the label is lowered, at most until its 12 px cell ends on the
        value top, to the first row that keeps the most characters (kept
        MicroPython difference).
        """
        k = self.k
        fit = self._fit(label, ly, LABEL, k, lo, hi, sh)
        if not fit[0]:
            for t in range(ly + 1, y - 12 + 1):
                ft = self._fit(label, t, LABEL, k, lo, hi, sh)
                if ft[0] > fit[0]:
                    ly, fit = t, ft
        return ly, fit

    def subtitle(self, *lines, color=DARK):
        """Draw subtitle text at the bottom (S). Accepts multiple lines."""
        if not lines:
            return
        k = self.k
        tws = [self._tw(line, TEXT, k) for line in lines]
        _, base_y = self._at("S", max(tws), k)
        line_h = self.u(self.CHAR_H + 3)
        n = len(lines)

        if n == 1:
            start_y = base_y + self.u(self.CHAR_H)
        else:
            block_h = (n - 1) * line_h
            start_y = base_y - block_h // 2

        if k > 1:
            # The block rises a row at a time until every line fits the
            # circle at its ink rows (8x16 cells), never above its last
            # line's top on the S row.
            masks = [
                fonts.masks(fonts.face(line, TEXT, k)[0], line)[-1] if line else 0
                for line in lines
            ]

            def fits(y):
                for i in range(n):
                    c = self._band(masks[i], y + i * line_h, 1)
                    if masks[i] and not (c and tws[i] <= c[1] - c[0] + 1):
                        return False
                return True

            while start_y > base_y - (n - 1) * line_h and not fits(start_y):
                start_y -= 1

        cx = self.width // 2
        for i, line in enumerate(lines):
            y = start_y + i * line_h
            if k > 1:
                self._put(line, cx, y, color, TEXT, k)
            else:
                self._txt(line, cx - len(line) * 4, y, color, 1, "draw_small_text")

    def bar(self, val, max_val=100, y_offset=0, color=LIGHT):
        """Draw a horizontal progress bar below center.

        A bar moved far from the centre by y_offset is cut to the circle on
        each of its rows (Arduino rule 7).
        """
        cx, cy = self.center
        bar_w = self.width - self.u(40)
        bar_h = self.u(8)
        bx = cx - bar_w // 2
        by = cy + self.u(20) + self.u(y_offset)
        fill_w = int(bar_w * min(val, max_val) / max_val) if max_val else 0

        self._bar_rows(bx, bx + bar_w - 1, by, bar_h, DARK)
        if fill_w > 0:
            self._bar_rows(bx, bx + fill_w - 1, by, bar_h, color)

    def _bar_rows(self, left, right, top, h, c):
        """Fill columns left..right of rows top..top + h - 1 inside the circle.

        One rect when the chord of the end rows (the narrower) holds the
        span, else one span per row, cut to that row's chord.
        """
        ch = self._chord(top, top + h - 1)
        if ch and ch[0] <= left and right <= ch[1]:
            self._fill_rect(left, top, right - left + 1, h, c)
            return
        for y in range(max(top, 0), min(top + h, self.height)):
            ch = self._chord(y, y)
            if ch:
                x0 = max(left, ch[0])
                x1 = min(right, ch[1], self.width - 1)
                if x0 <= x1:
                    self._fill_rect(x0, y, x1 - x0 + 1, 1, c)

    def gauge(self, val, min_val=0, max_val=100, color=LIGHT, arc_width=None):
        """Draw a circular arc gauge (270 deg, gap at bottom).

        The arc is drawn close to the screen border. Call gauge() before
        title() so that text layers on top of the arc.

        The fill sweeps int(270 * ratio) degrees, ratio = (val - min_val) /
        (max_val - min_val) clamped to 0..1, so a value with 0 < ratio <
        1/270 shows an empty gauge, as the Arduino gauge does.

        Args:
            val: Current value to display.
            min_val: Minimum value (empty gauge).
            max_val: Maximum value (full gauge).
            color: Color of the filled arc.
            arc_width: Optional custom arc thickness in pixels.
                       Defaults to max(5, radius // 9).
        """
        k = self.k
        cx, cy = self.center
        arc_w = arc_width if arc_width is not None else max(5, self.radius // 9)
        # Centre line of the ring; when k > 1 its outer edge is radius - u(4).
        r = self.radius - arc_w // 2 - (1 if k == 1 else self.u(4))
        start_angle = 135
        sweep = 270
        ratio = (val - min_val) / (max_val - min_val) if max_val != min_val else 0
        ratio = max(0.0, min(1.0, ratio))

        # Background arc
        self._draw_arc(cx, cy, r, start_angle, sweep, DARK, arc_w)
        # Filled arc
        if ratio > 0:
            self._draw_arc(cx, cy, r, start_angle, int(sweep * ratio), color, arc_w + 2)

        # Min/max labels, their top row on the point; when k > 1 at distance
        # outer - arc_w - u(10), in the 6x12 LABEL face, kept inside the circle.
        r_label = r - arc_w - self.u(10) + (0 if k == 1 else arc_w // 2)
        q = int if k == 1 else round
        for t, deg in (
            (str(int(min_val)), start_angle + 8),
            (str(int(max_val)), start_angle + sweep - 8),
        ):
            a = math.radians(deg)
            px = q(cx + r_label * math.cos(a))
            py = q(cy + r_label * math.sin(a))
            if k > 1:
                self._put(t, px, py, GRAY, LABEL, k, 1, 0, None, k)
            else:
                self._txt(t, px - len(t) * 4, py, GRAY, 1, "draw_small_text")

    def graph(self, data, min_val=0, max_val=100, color=LIGHT):
        """Draw a scrolling line graph with the current value above.

        The current value is the integer part of the last point, or "--"
        when data is empty or its last point is NaN or infinite (Arduino
        5.9). An infinite point is clamped to the box like any other. With 0
        or 1 point only the frame and the value are drawn. A NaN point is
        skipped and leaves a gap: no segment reaches it, and the other
        points keep their x. When k > 1 the value and the axis labels keep
        the longest prefix that fits the circle at their ink rows.
        """
        k = self.k
        u = self.u
        cx, _cy = self.center
        margin = u(STEAMI_GRAPH_MARGIN)
        gx = margin + u(STEAMI_GRAPH_X_OFFSET)
        gy = u(STEAMI_GRAPH_Y)
        gw = self.width - margin - gx
        gh = u(STEAMI_GRAPH_HEIGHT)

        text = "--"
        if data and math.isfinite(data[-1]):
            text = str(int(data[-1]))
        if k > 1:
            # Centred on cx, cut to the chord at its ink rows (rule 7).
            self._put(text, cx, u(STEAMI_GRAPH_VALUE_Y), WHITE, TEXT, k)
        else:
            tw = self._tw(text, TEXT, k)
            self._txt(text, cx - tw // 2, u(STEAMI_GRAPH_VALUE_Y), WHITE, k, "draw_medium_text")

        def _fmt(v):
            if v >= 1000 and v % 1000 == 0:
                return str(int(v // 1000)) + "k"
            return str(int(v))

        mid_y = gy + gh // 2
        mid_val = (min_val + max_val) / 2
        for val, yp in ((max_val, gy), (mid_val, mid_y), (min_val, gy + gh)):
            label = _fmt(val)
            if k == 1:
                # Left of the axis, centred on its line.
                cw = int(self.CHAR_W * 0.85)
                self._txt(label, gx - len(label) * cw - 1, yp - 4, DARK, 1, "draw_small_text")
                continue
            # Inside the box, where the circle leaves room (Arduino 5.9), in
            # the 6x12 LABEL face: the max label's first ink row u(2) below
            # the top, the others' last ink row k + u(2) above their line.
            # Left edge gx + k + u(2), cut to the chord at its ink rows less
            # k (Arduino drawGraphLabel(), rule 7).
            # Kept MicroPython difference: three labels, with "k" formatting.
            fc = fonts.face(label, LABEL, k)[0]
            a, b = fonts.ink_rows(fonts.masks(fc, label)[-1])
            y = gy + u(2) - a if yp == gy else yp - k - u(2) - b
            lx = gx + k + u(2)
            self._put(label, lx, y, DARK, LABEL, k, 0, lx, None, k)

        dash, gap = u(STEAMI_GRAPH_DASH), u(STEAMI_GRAPH_GAP)
        x = gx + k
        while x < gx + gw:
            x2 = min(x + dash - 1, gx + gw - 1)
            self._line(x, mid_y, x2, mid_y, GRID_DARK)
            x += dash + gap

        self._sline(gx, gy, gx, gy + gh, DARK)
        self._sline(gx, gy + gh, gx + gw - 1, gy + gh, DARK)

        if len(data) < 2:
            return

        step = gw / (len(data) - 1) if len(data) > 1 else gw
        span = max_val - min_val
        if span == 0:
            span = 1

        prev_px, prev_py = None, None
        for i, v in enumerate(data):
            if math.isnan(v):
                prev_px = None
                continue
            px = int(gx + i * step)
            ratio = (v - min_val) / span
            ratio = max(0.0, min(1.0, ratio))
            py = int(gy + gh - ratio * gh)
            if prev_px is not None:
                self._sline(prev_px, prev_py, px, py, color)
            prev_px, prev_py = px, py

    def menu(self, items, selected=0, color=WHITE):
        """Draw a scrollable list menu."""
        k = self.k
        u = self.u
        item_h = u(self.CHAR_H + 6)
        visible = min(len(items), (self.height - 40) // item_h)
        if k > 1:
            # Rows u(35 + 14 j) whose chord holds the marker and 10 cells.
            # Kept MicroPython difference: Arduino shows 6 rows with a bar
            # clipped per scanline; here 5 rows (192 px chords) on 240 px.
            visible = 0
            while visible < len(items):
                y = u(35 + 14 * visible)
                c = self._chord(y, y + 8 * k - 1)
                if not c or c[1] - c[0] + 1 < STEAMI_MENU_ROW_CELLS * 8 * k:
                    break
                visible += 1
        start = max(0, min(selected - visible // 2, len(items) - visible))
        x = u(18)

        for i in range(start, min(start + visible, len(items))):
            iy = u(35 + 14 * (i - start))
            if i == selected:
                self._fill_rect(u(15), iy - u(2), self.width - u(30), item_h, DARK)
                text, c = "> " + items[i], color
            else:
                text, c = "  " + items[i], GRAY
            if k > 1:
                self._put(text, x, iy, c, TEXT, k, 0, x, None, k)
            else:
                self._text8(text, x, iy, c, 1, "text")

    def compass(self, heading, color=LIGHT):
        """Draw a compass with a rotating needle."""
        k = self.k
        u = self.u
        q = int if k == 1 else round
        cx, cy = self.center
        r = self.radius - u(12)

        self._ring(cx, cy, r, DARK)
        self._ring(cx, cy, int(r * 0.7), DARK)

        for label, angle in (("N", 0), ("E", 90), ("S", 180), ("W", 270)):
            lx = cx + q((r + u(5)) * math.sin(math.radians(angle)))
            ly = cy - q((r + u(5)) * math.cos(math.radians(angle)))
            c = WHITE if label == "N" else GRAY
            # The letter's cell centred on the point (8x16 on 240 px).
            self._txt(
                label, lx - self._tw(label, TEXT, k) // 2, ly - self.text_height() // 2, c, k
            )

        for angle in range(0, 360, 45):
            inner = r - u(6)
            outer = r
            rad = math.radians(angle)
            x1 = cx + q(inner * math.sin(rad))
            y1 = cy - q(inner * math.cos(rad))
            x2 = cx + q(outer * math.sin(rad))
            y2 = cy - q(outer * math.cos(rad))
            c = LIGHT if angle % 90 == 0 else DARK
            self._sline(x1, y1, x2, y2, c)

        rad = math.radians(heading)
        needle_len = int(r * 0.85)
        half_w = u(3)

        nx = cx + q(needle_len * math.sin(rad))
        ny = cy - q(needle_len * math.cos(rad))
        sx = cx - q(needle_len * math.sin(rad))
        sy = cy + q(needle_len * math.cos(rad))
        px = q(half_w * math.cos(rad))
        py = q(half_w * math.sin(rad))

        self._fill_triangle(nx, ny, cx - px, cy - py, cx + px, cy + py, color)
        self._fill_triangle(sx, sy, cx - px, cy - py, cx + px, cy + py, DARK)
        self._fill_circle(cx, cy, u(3), GRAY)

    def watch(self, hours, minutes, seconds=0, color=LIGHT):
        """Draw an analog watch face."""
        k = self.k
        u = self.u
        q = int if k == 1 else round
        cx, cy = self.center
        r = self.radius - u(8)

        self._ring(cx, cy, r, DARK)

        for i in range(12):
            angle = i * 30
            rad = math.radians(angle)
            if i % 3 == 0:
                inner = r - u(8)
                c = LIGHT
            else:
                inner = r - u(5)
                c = GRAY
            x1 = cx + q(inner * math.sin(rad))
            y1 = cy - q(inner * math.cos(rad))
            x2 = cx + q(r * math.sin(rad))
            y2 = cy - q(r * math.cos(rad))
            self._sline(x1, y1, x2, y2, c)

        for num, angle in ((12, 0), (3, 90), (6, 180), (9, 270)):
            text = str(num)
            rad = math.radians(angle)
            lx = cx + q((r - u(15)) * math.sin(rad))
            ly = cy - q((r - u(15)) * math.cos(rad))
            tw = self._tw(text, TEXT, k)
            self._txt(text, lx - tw // 2, ly - self.text_height() // 2, WHITE, k)

        # Hands: (angle in degrees, length, half width), then the second hand.
        for deg, length, half in (
            ((hours % 12 + minutes / 60) * 30, int(r * 0.50), u(3)),
            ((minutes + seconds / 60) * 6, int(r * 0.75), u(2)),
        ):
            rad = math.radians(deg)
            hx = cx + q(length * math.sin(rad))
            hy = cy - q(length * math.cos(rad))
            px = q(half * math.cos(rad))
            py = q(half * math.sin(rad))
            self._fill_triangle(hx, hy, cx - px, cy - py, cx + px, cy + py, color)

        s_rad = math.radians(seconds * 6)
        s_len = int(r * 0.85)
        sx = cx + q(s_len * math.sin(s_rad))
        sy = cy - q(s_len * math.cos(s_rad))
        self._sline(cx, cy, sx, sy, GRAY)
        self._fill_circle(cx, cy, u(3), GRAY)

    def face(self, expression, compact=False, color=LIGHT):
        """Draw a pixel-art face expression (8x8 bitmap scaled up)."""
        if isinstance(expression, str):
            bitmap = FACES.get(expression)
            if bitmap is None:
                return
        else:
            bitmap = expression

        cx, cy = self.center
        if compact:
            scale = self.width // 16  # 8 on 128px
            ox = cx - 4 * scale
            oy = cy - 4 * scale - scale // 2
        else:
            scale = (self.width * 11) // 128
            ox = cx - 4 * scale
            oy = cy - 4 * scale

        for row in range(8):
            byte = bitmap[row]
            for col in range(8):
                if byte & (0x80 >> col):
                    self._fill_rect(ox + col * scale, oy + row * scale, scale, scale, color)

    # --- Level 2: Cardinal text & shapes ---

    def text(self, text, at="CENTER", color=WHITE, scale=1):
        """Draw text at a cardinal position or explicit (x,y).

        At a cardinal position the glyphs are scaled by k (Spleen 8x16 x scale
        on 240 px) and, when k > 1, the text is kept inside the circle (moved,
        then cut at the chord of its ink rows). An explicit (x, y) is in real
        pixels, the top left of the first cell: the 8x8
        font x scale on 128 px, Spleen 8x16 x scale on 240 px (accents
        included, any other character drawn as '?'). A scale below 1
        counts as 1.
        """
        scale = max(scale, 1)
        if isinstance(at, str):
            k = self.k
            f = scale * k
            x, y = self._at(at, self._tw(text, TEXT, f), f)
            if k > 1:
                # W runs from its margin to the chord's right edge - k, E is its
                # mirror image, a corner takes the chord shrunk by k.
                w = self.width
                me = self._margin_ew(f)
                if at in ("NW", "W", "SW"):
                    self._put(text, me, y, color, TEXT, f, 0, me if at == "W" else 0, None, k)
                elif at in ("NE", "E", "SE"):
                    hi = w - me - 1 if at == "E" else None
                    self._put(text, w - me, y, color, TEXT, f, 2, 0, hi, k)
                else:
                    self._put(text, w // 2, y, color, TEXT, f)
                return
            scale = f
        else:
            x, y = at
            if self.k > 1:
                self._draw(text, x, y, color, TEXT, scale * self.k)
                return
        self._txt(text, x, y, color, scale)

    def line(self, x1, y1, x2, y2, color=WHITE):
        self._line(x1, y1, x2, y2, color)

    def circle(self, x, y, r, color=WHITE, fill=False):
        if fill:
            self._fill_circle(x, y, r, color)
        else:
            self._draw_circle(x, y, r, color)

    def rect(self, x, y, w, h, color=WHITE, fill=False):
        if fill:
            self._fill_rect(x, y, w, h, color)
        else:
            self._rect(x, y, w, h, color)

    def pixel(self, x, y, color=WHITE):
        self._d.pixel(x, y, color)

    # --- Control ---

    def clear(self, color=BLACK):
        self._d.fill(color)

    def show(self):
        self._d.show()

    # --- Internal drawing helpers ---

    def _line(self, x1, y1, x2, y2, c):
        self._d.line(x1, y1, x2, y2, c)

    def _sline(self, x1, y1, x2, y2, c):
        """Line k px wide: a k x k brush along the line."""
        k = self.k
        o = (k - 1) // 2
        for i in range(k * k):
            dx, dy = i % k - o, i // k - o
            self._line(x1 + dx, y1 + dy, x2 + dx, y2 + dy, c)

    def _ring(self, cx, cy, r, c):
        """Circle outline k px wide (Bresenham when k = 1).

        When k > 1, the ring between radii r - k + 1 - 1/2 and r + 1/2, as
        the Arduino arc().
        """
        k = self.k
        if k == 1:
            self._draw_circle(cx, cy, r, c)
            return
        ri = max(0, r - k + 1)
        for dy in range(-r, r + 1):
            d4 = 4 * dy * dy
            xo = int(math.sqrt(((2 * r + 1) ** 2 - d4) // 4))
            xi = 0
            q = ((2 * ri - 1) ** 2 - d4 + 3) // 4
            if ri and q > 0:
                xi = int(math.sqrt(q))
                xi += xi * xi < q
            y = cy + dy
            if not xi:
                self._line(cx - xo, y, cx + xo, y, c)
            elif xi <= xo:
                self._line(cx - xo, y, cx - xi, y, c)
                self._line(cx + xi, y, cx + xo, y, c)

    def _txt(self, s, x, y, c, f=1, alt="text", ink=TEXT):
        """Text at glyph factor f, (x, y) the top left of its first cell.

        When k > 1, the Spleen face of `ink` at f. When k == 1, the 8x8 font
        through _text8: at f 1 through the backend's `alt` method if any.
        """
        if self.k > 1:
            self._draw(s, x, y, c, ink, f)
        else:
            self._text8(s, x, y, c, f, alt)

    def _text8(self, s, x, y, c, f, alt):
        """8x8 text at factor f, accents folded and '°' drawn by _degree8.

        s is split at '°' before folding, so a literal "\\x7f" stays a framebuf
        glyph. Each segment goes to draw_scaled_text when alt is None or
        f > 1, else to the backend's `alt` method if any. The pen advances
        8f per cell the segment's drawer draws: one per character for
        draw_scaled_text, one per UTF-8 byte for framebuf.text. A text
        without '°' is one call, as before.
        """
        if "°" not in s:
            self._seg8(fonts.fold8(s), x, y, c, f, alt)
            return
        first = True
        for seg in s.split("°"):
            if not first:
                self._degree8(x, y, c, f)
                x += 8 * f
            first = False
            if seg:
                seg = fonts.fold8(seg)
                self._seg8(seg, x, y, c, f, alt)
                if alt is None or f > 1:
                    x += len(seg) * 8 * f
                else:
                    x += len(seg.encode()) * 8

    def _seg8(self, s, x, y, c, f, alt):
        if alt is None or f > 1:
            self._draw_scaled_text(s, x, y, c, f)
        else:
            getattr(self._d, alt, self._d.text)(s, x, y, c)

    def _degree8(self, x, y, c, f):
        """Arduino's 8x8 degree sign at (x, y), f x f per font pixel."""
        fonts.draw_runs(self._fill_rect, fonts.DEGREE8, ((0, x, y),), f, 0, c)

    def _hline(self, x, y, w, c):
        self._d.line(x, y, x + w - 1, y, c)

    def _vline(self, x, y, h, c):
        self._d.line(x, y, x, y + h - 1, c)

    def _fill_rect(self, x, y, w, h, c):
        if hasattr(self._d, "fill_rect"):
            self._d.fill_rect(x, y, w, h, c)
        else:
            for row in range(h):
                self._d.line(x, y + row, x + w - 1, y + row, c)

    def _rect(self, x, y, w, h, c):
        if hasattr(self._d, "rect"):
            self._d.rect(x, y, w, h, c)
        else:
            self._hline(x, y, w, c)
            self._hline(x, y + h - 1, w, c)
            self._vline(x, y, h, c)
            self._vline(x + w - 1, y, h, c)

    def _draw_scaled_text(self, text, x, y, color, scale):
        """Draw text at scale > 1.

        If the backend provides ``draw_scaled_text()``, it is used directly.
        Otherwise, the text is drawn multiple times with a 1px offset to
        produce a bold effect (not a true pixel-scale zoom).
        """
        if hasattr(self._d, "draw_scaled_text"):
            self._d.draw_scaled_text(text, x, y, color, scale)
            return
        # On real hardware without scaled text support, draw at scale=1
        # centered at the same position (best effort)
        if not hasattr(self._d, "pixel"):
            self._d.text(text, x, y, color)
            return
        if scale == 2:
            for dx in range(2):
                for dy in range(2):
                    self._d.text(text, x + dx, y + dy, color)
        elif scale == 3:
            for dx in range(3):
                for dy in range(3):
                    self._d.text(text, x + dx, y + dy, color)
        else:
            self._d.text(text, x, y, color)

    def _draw_arc(self, cx, cy, r, start_deg, sweep_deg, color, width=3):
        """Draw a thick arc: the ring r - width // 2 .. r + width // 2.

        Angles are in degrees, 0 at 3 o'clock, growing clockwise on the
        screen (y down); sweep <= 0 draws nothing, sweep >= 360 a full ring.
        As the Arduino arc(), each row of the ring is clipped to the sector
        with two integer cross products, then drawn as horizontal spans:
        every pixel is decided once, so the ring has no holes.

        The rows allocate nothing: the colour is converted once and each span
        goes straight to the driver's fill_rect (native_fill() of the
        adapter), and the square roots are integers, moved one step at a
        time from the previous row.
        """
        if hasattr(self._d, "draw_arc"):
            self._d.draw_arc(cx, cy, r, start_deg, sweep_deg, color, width)
            return
        if sweep_deg <= 0:
            return
        half = width // 2
        ro, ri = r + half, max(0, r - half)
        # Sectors of at most 180 deg: (start ray, end ray), Q14 cos and sin.
        secs = ()
        if sweep_deg < 360:
            m = start_deg + min(sweep_deg, 180)
            secs = (_ray(start_deg) + _ray(m),)
            if sweep_deg > 180:
                secs += (_ray(m) + _ray(start_deg + sweep_deg),)
        o2, i2 = (2 * ro + 1) ** 2, (2 * ri - 1) ** 2
        if hasattr(self._d, "native_fill"):
            fr, color = self._d.native_fill(color)
        else:
            fr = self._fill_rect
        xo = si = 0
        for dy in range(max(-ro, -cy), min(ro, self.height - 1 - cy) + 1):
            d4 = 4 * dy * dy
            # xo = floor(sqrt(n)) and xi = ceil(sqrt(q)), q > 0: the outer
            # and inner edges of the ring on this row.
            n = (o2 - d4) // 4
            while xo * xo > n:
                xo -= 1
            while (xo + 1) * (xo + 1) <= n:
                xo += 1
            xi = 0
            q = (i2 - d4 + 3) // 4
            if ri and q > 0:
                while si * si > q:
                    si -= 1
                while (si + 1) * (si + 1) <= q:
                    si += 1
                xi = si + (si * si < q)
            if xi > xo:
                continue
            y = cy + dy
            # One span -xo..xo, or two: -xo..-xi, then xi..xo.
            lo, hi = -xo, -xi if xi else xo
            while True:
                if not secs:
                    fr(cx + lo, y, hi - lo + 1, 1, color)
                # On row dy each half-plane cross(S, p) >= 0, cross(p, E) >= 0
                # is a half-line in dx: clip the span to both.
                for sx, sy, ex, ey in secs:
                    a, b = lo, hi
                    c = sx * dy
                    if sy > 0:
                        b = min(b, c // sy)
                    elif sy < 0:
                        a = max(a, -(c // -sy))
                    elif c < 0:
                        continue
                    c = ex * dy
                    if ey > 0:
                        a = max(a, -(-c // ey))
                    elif ey < 0:
                        b = min(b, c // ey)
                    elif c > 0:
                        continue
                    if a <= b:
                        fr(cx + a, y, b - a + 1, 1, color)
                if lo > 0 or not xi:
                    break
                lo, hi = xi, xo

    def _draw_circle(self, cx, cy, r, color):
        """Bresenham circle."""
        x, y, d = r, 0, 1 - r
        while x >= y:
            for sx, sy in ((x, y), (y, x), (-x, y), (-y, x), (x, -y), (y, -x), (-x, -y), (-y, -x)):
                px, py = cx + sx, cy + sy
                if 0 <= px < self.width and 0 <= py < self.height:
                    self._d.pixel(px, py, color)
            y += 1
            if d < 0:
                d += 2 * y + 1
            else:
                x -= 1
                d += 2 * (y - x) + 1

    def _fill_circle(self, cx, cy, r, color):
        """Filled circle using horizontal lines."""
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(r * r - dy * dy))
            y = cy + dy
            if 0 <= y < self.height:
                x1 = max(0, cx - dx)
                x2 = min(self.width - 1, cx + dx)
                self._line(x1, y, x2, y, color)

    def _fill_triangle(self, x0, y0, x1, y1, x2, y2, color):
        """Filled triangle using scanline."""
        pts = sorted([(x0, y0), (x1, y1), (x2, y2)], key=lambda p: p[1])
        (ax, ay), (bx, by), (cx, cy_) = pts

        def interp(ya, xa, yb, xb, y):
            if yb == ya:
                return xa
            return xa + (xb - xa) * (y - ya) // (yb - ya)

        for y in range(ay, cy_ + 1):
            if y < by:
                xl = interp(ay, ax, cy_, cx, y)
                xr = interp(ay, ax, by, bx, y)
            else:
                xl = interp(ay, ax, cy_, cx, y)
                xr = interp(by, bx, cy_, cx, y)
            if xl > xr:
                xl, xr = xr, xl
            if 0 <= y < self.height:
                x_start = max(0, xl)
                x_end = min(self.width - 1, xr)
                if x_start <= x_end:
                    self._line(x_start, y, x_end, y, color)
