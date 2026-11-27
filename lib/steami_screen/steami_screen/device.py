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
Primitives and text(s, at=(x, y)) take real pixels and are never scaled.
"""

import math

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
        return self.width // (self.CHAR_W * self.k)

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
        of a 13-cell text (wider text is cut there).
        """
        k = self.k
        cx, cy = self.center
        r = self.radius
        h = tw // 2
        if k > 1:
            h = min(h, STEAMI_TITLE_CAP_CELLS * 4 * k)
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

    def _ink(self, s):
        """Row masks of the prefixes of s: bit i is set when a glyph inks row i."""
        import framebuf

        b = bytearray(8)
        fb = framebuf.FrameBuffer(b, 8, 8, framebuf.MONO_HLSB)
        m = 0
        out = []
        for ch in s:
            fb.fill(0)
            fb.text(ch, 0, 0, 1)
            for i in range(8):
                if b[i]:
                    m |= 1 << i
            out.append(m)
        return out

    def _band(self, m, y, f):
        """Chord at the rows that mask m inks (glyph factor f, top y); the panel if none."""
        if not m:
            return 0, self.width - 1
        a = 0
        while not m >> a & 1:
            a += 1
        b = 7
        while not m >> b & 1:
            b -= 1
        return self._chord(y + a * f, y + b * f + f - 1)

    def _fit(self, s, y, f, lo=0, hi=None, shrink=0, pad=0):
        """Longest prefix of s that fits [lo, hi] and the chord at its inked rows.

        The chord is shrunk by `shrink` at each end. Returns (n, lo, hi): the
        characters kept and the room they fit in.
        """
        if hi is None:
            hi = self.width - 1
        pre = self._ink(s)
        n = len(s)
        while n:
            m = pre[n - 1]
            c = self._band(m, y, f)
            if c:
                left, right = max(c[0] + shrink, lo), min(c[1] - shrink, hi)
                if not m or n * 8 * f + pad <= right - left + 1:
                    return n, left, right
            n -= 1
        return 0, lo, hi

    def _put(self, s, ax, y, color, f, align=1, lo=0, hi=None, shrink=0, pad=0):
        """Draw the longest prefix of s that fits (see _fit), at glyph factor f.

        align: 0 left edge at ax, 1 centred on ax, 2 right edge before ax,
        3 centred in the room. x is clamped into the room. Returns (x, width).
        """
        n, lo, hi = self._fit(s, y, f, lo, hi, shrink, pad)
        w = n * 8 * f
        if align == 3:
            ax, align = (lo + hi + 1) // 2, 1
        x = max(lo, min(ax - (0, w // 2, w)[align], hi - w + 1))
        if n:
            self._draw_scaled_text(s[:n], x, y, color, f)
        return x, w

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
            self._d.text(label, lx, y - self.CHAR_H - 4, GRAY)

        self._draw_scaled_text(text, x, y, color, scale)

        if unit:
            unit_y = y + char_h
            ux = x + tw // 2 - len(unit) * self.CHAR_W // 2
            self._txt(unit, ux, unit_y, LIGHT, 1, "draw_medium_text")

    def _value(self, text, unit, at, label, color, scale, y_offset):
        """value() when k > 1: Arduino's fit of the value, its label and unit.

        The glyph factor goes from scale * k down to 1 until the value fits
        its region; at 1 the value is cut. W and E use the half region of
        their side, sized for the widest of the text and "88.8".
        """
        k = self.k
        f = max(scale, 1) * k
        cx, cy = self.center
        w = self.width
        gap = self.u(STEAMI_VALUE_SIDE_GAP)
        side = at in ("W", "E")
        corner = at in ("NE", "NW", "SE", "SW")
        pad = 0 if side or corner else self.u(STEAMI_VALUE_FIT_MARGIN)
        while True:
            vw = len(text) * 8 * f
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
                # B6: "88.8" sets the factor of every narrower value at W/E.
                fits = max(vw, 32 * f) <= hi - lo + 1 if side else lo <= x <= hi - vw + 1
            else:
                fits = self._fit(text, y, f, lo, hi, 0, pad)[0] == len(text)
            if fits or f == 1:
                break
            f -= 1
        if side:
            ax, align = 0, 3
        elif corner:
            ax, align = x, 0
            if at[1] == "E":
                ax, align = x + vw, 2
        else:
            ax, align = cx, 1
        vx, vw = self._put(text, ax, y, color, f, align, lo, hi, 0, pad)
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
            ly = y - self.u(4) - 8 * k
            if not self._fit(label, ly, k, lo, hi, sh)[0]:
                # Near the top its rows can leave the circle: lower it, at
                # most down to the value, to the row that keeps the most.
                best = 0
                for t in range(ly + 1, y - 8 * k + 1):
                    n = self._fit(label, t, k, lo, hi, sh)[0]
                    if n > best:
                        best, ly = n, t
            self._put(label, ax, ly, GRAY, k, align, lo, hi, sh)
        if unit:
            self._put(unit, ax, y + 8 * f, LIGHT, k, align, lo, hi, sh)

    def subtitle(self, *lines, color=DARK):
        """Draw subtitle text at the bottom (S). Accepts multiple lines."""
        if not lines:
            return
        k = self.k
        max_len = max(len(line) for line in lines)
        _, base_y = self._at("S", max_len * 8 * k, k)
        line_h = self.u(self.CHAR_H + 3)
        n = len(lines)

        if n == 1:
            start_y = base_y + self.u(self.CHAR_H)
        else:
            block_h = (n - 1) * line_h
            start_y = base_y - block_h // 2

        if k > 1:
            # The block rises a row at a time until every line fits the
            # circle, never above its last line's top on the S row.
            masks = [self._ink(line)[-1] if line else 0 for line in lines]

            def fits(y):
                for i, line in enumerate(lines):
                    c = self._band(masks[i], y + i * line_h, k)
                    if masks[i] and not (c and len(line) * 8 * k <= c[1] - c[0] + 1):
                        return False
                return True

            while start_y > base_y - (n - 1) * line_h and not fits(start_y):
                start_y -= 1

        cx = self.width // 2
        for i, line in enumerate(lines):
            y = start_y + i * line_h
            if k > 1:
                self._put(line, cx, y, color, k)
            else:
                self._txt(line, cx - len(line) * 4, y, color, 1, "draw_small_text")

    def bar(self, val, max_val=100, y_offset=0, color=LIGHT):
        """Draw a horizontal progress bar below center."""
        cx, cy = self.center
        bar_w = self.width - self.u(40)
        bar_h = self.u(8)
        bx = cx - bar_w // 2
        by = cy + self.u(20) + self.u(y_offset)
        fill_w = int(bar_w * min(val, max_val) / max_val) if max_val else 0

        self._fill_rect(bx, by, bar_w, bar_h, DARK)
        if fill_w > 0:
            self._fill_rect(bx, by, fill_w, bar_h, color)

    def gauge(self, val, min_val=0, max_val=100, color=LIGHT, arc_width=None):
        """Draw a circular arc gauge (270 deg, gap at bottom).

        The arc is drawn close to the screen border. Call gauge() before
        title() so that text layers on top of the arc.

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
        # outer - arc_w - u(10), kept inside the circle.
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
                self._put(t, px, py, GRAY, k, 1, 0, None, k)
            else:
                self._txt(t, px - len(t) * 4, py, GRAY, 1, "draw_small_text")

    def graph(self, data, min_val=0, max_val=100, color=LIGHT):
        """Draw a scrolling line graph with the current value above."""
        k = self.k
        u = self.u
        cx, _cy = self.center
        margin = u(STEAMI_GRAPH_MARGIN)
        gx = margin + u(STEAMI_GRAPH_X_OFFSET)
        gy = u(STEAMI_GRAPH_Y)
        gw = self.width - margin - gx
        gh = u(STEAMI_GRAPH_HEIGHT)

        if data:
            text = str(int(data[-1]))
            tw = len(text) * 8 * k
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
            # Inside the box, where the circle leaves room (Arduino 5.9): the
            # max label's top u(2) below the top, the others' last inked row
            # (digits ink rows 0-6) k + u(2) above their line.
            y = yp + u(2) if yp == gy else yp - u(2) - 8 * k + 1
            self._txt(label, gx + k + u(2), y, DARK, k)

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
                self._put(text, x, iy, c, k, 0, x, None, k)
            else:
                self._d.text(text, x, iy, c)

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
            self._txt(label, lx - 4 * k, ly - 4 * k, c, k)

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
            tw = len(text) * 8 * k
            self._txt(text, lx - tw // 2, ly - 4 * k, WHITE, k)

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

        At a cardinal position the glyphs are scaled by k and, when k > 1,
        the text is kept inside the circle (moved, then cut). An explicit
        (x, y) is in real pixels and the scale is used as given. A scale
        below 1 counts as 1.
        """
        scale = max(scale, 1)
        if isinstance(at, str):
            k = self.k
            f = scale * k
            x, y = self._at(at, len(text) * 8 * f, f)
            if k > 1:
                # W runs from its margin to the chord's right edge - k, E is its
                # mirror image, a corner takes the chord shrunk by k.
                w = self.width
                me = self._margin_ew(f)
                if at in ("NW", "W", "SW"):
                    self._put(text, me, y, color, f, 0, me if at == "W" else 0, None, k)
                elif at in ("NE", "E", "SE"):
                    self._put(
                        text, w - me, y, color, f, 2, 0, w - me - 1 if at == "E" else None, k
                    )
                else:
                    self._put(text, w // 2, y, color, f)
                return
            scale = f
        else:
            x, y = at
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

    def _txt(self, s, x, y, c, f=1, alt="text"):
        """Text at glyph factor f; at 1 through the backend's `alt` method if any."""
        if f > 1:
            self._draw_scaled_text(s, x, y, c, f)
        else:
            getattr(self._d, alt, self._d.text)(s, x, y, c)

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
        fr = self._fill_rect
        for dy in range(max(-ro, -cy), min(ro, self.height - 1 - cy) + 1):
            d4 = 4 * dy * dy
            xo = int(math.sqrt((o2 - d4) // 4))
            xi = 0
            q = (i2 - d4 + 3) // 4
            if ri and q > 0:
                xi = int(math.sqrt(q))
                xi += xi * xi < q
            if xi > xo:
                continue
            y = cy + dy
            for lo, hi in ((-xo, -xi), (xi, xo)) if xi else ((-xo, xo),):
                if not secs:
                    fr(cx + lo, y, hi - lo + 1, 1, color)
                    continue
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
