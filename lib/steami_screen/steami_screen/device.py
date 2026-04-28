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
"""

import math

# --- Color constants (RGB tuples) ---
# Grays map to exact SSD1327 levels: gray4 * 17 gives R=G=B
BLACK = (0, 0, 0)
DARK = (102, 102, 102)  # gray4=6
GRAY = (153, 153, 153)  # gray4=9
LIGHT = (187, 187, 187)  # gray4=11
WHITE = (255, 255, 255)  # gray4=15

# Accent colors (used on color displays, degrade gracefully to gray on SSD1327)
GREEN = (119, 255, 119)
RED = (255, 85, 85)
BLUE = (85, 85, 255)
YELLOW = (255, 255, 85)

# --- Pixel-art face bitmaps (8x8, MSB = left) ---
FACES = {
    "happy": (0x00, 0x24, 0x24, 0x00, 0x00, 0x42, 0x3C, 0x00),
    "sad": (0x00, 0x24, 0x24, 0x00, 0x00, 0x3C, 0x42, 0x00),
    "surprised": (0x00, 0x24, 0x24, 0x00, 0x18, 0x24, 0x24, 0x18),
    "sleeping": (0x00, 0x00, 0x66, 0x00, 0x00, 0x18, 0x18, 0x00),
    "angry": (0x00, 0x42, 0x24, 0x24, 0x00, 0x3C, 0x42, 0x00),
    "love": (0x00, 0x66, 0xFF, 0xFF, 0x7E, 0x3C, 0x18, 0x00),
}

# --- Cardinal position names ---


class Screen:
    """High-level wrapper around a raw display backend."""

    CHAR_W = 8  # framebuf built-in font width
    CHAR_H = 8  # framebuf built-in font height

    def __init__(self, display, width=None, height=None):
        self._d = display
        self.width = width or getattr(display, "width", 128)
        self.height = height or getattr(display, "height", 128)

    # --- Adaptive properties ---

    @property
    def center(self):
        return (self.width // 2, self.height // 2)

    @property
    def radius(self):
        return min(self.width, self.height) // 2

    @property
    def max_chars(self):
        return self.width // self.CHAR_W

    # --- Cardinal position resolver ---

    def _safe_margin(self, tw, from_edge):
        """Compute the minimum Y margin from top/bottom so that text of
        width `tw` fits inside the circle. `from_edge` is the baseline
        distance from the circle edge."""
        r = self.radius
        half_tw = tw / 2
        if half_tw >= r:
            return r
        max_d = math.sqrt(r * r - half_tw * half_tw)
        min_margin = r - int(max_d)
        return max(min_margin + 2, from_edge)

    def _resolve(self, at, text_len=0, scale=1):
        """Return (x, y) for a cardinal position, centering text if needed."""
        cx, cy = self.center
        ch = self.CHAR_H * scale
        tw = text_len * self.CHAR_W * scale

        margin_ns = self._safe_margin(tw, ch * 2 + 4)
        margin_ew = ch + 4

        positions = {
            "N": (cx - tw // 2, margin_ns),
            "NE": (self.width - margin_ew - tw, margin_ns),
            "E": (self.width - margin_ew - tw, cy - ch // 2),
            "SE": (self.width - margin_ew - tw, self.height - margin_ns - ch),
            "S": (cx - tw // 2, self.height - margin_ns - ch),
            "SW": (margin_ew, self.height - margin_ns - ch),
            "W": (margin_ew, cy - ch // 2),
            "NW": (margin_ew, margin_ns),
            "CENTER": (cx - tw // 2, cy - ch // 2),
        }
        return positions.get(at, positions["CENTER"])

    # --- Level 1: Widgets ---

    def title(self, text, color=GRAY):
        """Draw title text at the top (N)."""
        x, y = self._resolve("N", len(text))
        self._d.text(text, x, y, color)

    def value(
        self, val, unit=None, at="CENTER", label=None, color=WHITE, scale=2, y_offset=0
    ):
        """Draw a large value, optionally with unit below and label above."""
        text = str(val)
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
            x, y = self._resolve(at, len(text), scale)

        if label:
            lx = x + tw // 2 - len(label) * self.CHAR_W // 2
            self._d.text(label, lx, y - self.CHAR_H - 4, GRAY)

        self._draw_scaled_text(text, x, y, color, scale)

        if unit:
            unit_y = y + char_h
            ux = x + tw // 2 - len(unit) * self.CHAR_W // 2
            if hasattr(self._d, "draw_medium_text"):
                self._d.draw_medium_text(unit, ux, unit_y, LIGHT)
            else:
                self._d.text(unit, ux, unit_y, LIGHT)

    def subtitle(self, *lines, color=DARK):
        """Draw subtitle text at the bottom (S). Accepts multiple lines."""
        if not lines:
            return
        max_len = max(len(line) for line in lines)
        _, base_y = self._resolve("S", max_len)
        line_h = self.CHAR_H + 3
        n = len(lines)

        if n == 1:
            start_y = base_y + self.CHAR_H
        else:
            block_h = (n - 1) * line_h
            start_y = base_y - block_h // 2

        draw = getattr(self._d, "draw_small_text", self._d.text)
        for i, line in enumerate(lines):
            x, _ = self._resolve("S", len(line))
            y = start_y + i * line_h
            draw(line, x, y, color)

    def bar(self, val, max_val=100, y_offset=0, color=LIGHT):
        """Draw a horizontal progress bar below center."""
        cx, cy = self.center
        bar_w = self.width - 40
        bar_h = 8
        bx = cx - bar_w // 2
        by = cy + 20 + y_offset
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
        cx, cy = self.center
        arc_w = arc_width if arc_width is not None else max(5, self.radius // 9)
        r = self.radius - arc_w // 2 - 1
        start_angle = 135
        sweep = 270
        ratio = (val - min_val) / (max_val - min_val) if max_val != min_val else 0
        ratio = max(0.0, min(1.0, ratio))

        # Background arc
        self._draw_arc(cx, cy, r, start_angle, sweep, DARK, arc_w)
        # Filled arc
        if ratio > 0:
            self._draw_arc(cx, cy, r, start_angle, int(sweep * ratio), color, arc_w + 2)

        # Min/max labels
        min_t = str(int(min_val))
        max_t = str(int(max_val))
        r_label = r - arc_w - 10
        angle_s = math.radians(start_angle + 8)
        angle_e = math.radians(start_angle + sweep - 8)
        lx = int(cx + r_label * math.cos(angle_s)) - len(min_t) * self.CHAR_W // 2
        ly = int(cy + r_label * math.sin(angle_s))
        rx = int(cx + r_label * math.cos(angle_e)) - len(max_t) * self.CHAR_W // 2
        ry = int(cy + r_label * math.sin(angle_e))
        draw_sm = getattr(self._d, "draw_small_text", self._d.text)
        draw_sm(min_t, lx, ly, GRAY)
        draw_sm(max_t, rx, ry, GRAY)

    def graph(self, data, min_val=0, max_val=100, color=LIGHT):
        """Draw a scrolling line graph with the current value above."""
        cx, _cy = self.center
        margin = 15
        gx = margin + 6
        gy = 38
        gw = self.width - margin - gx
        gh = 52

        if data:
            text = str(int(data[-1]))
            draw_fn = getattr(self._d, "draw_medium_text", self._d.text)
            tw = len(text) * self.CHAR_W
            vx = cx - tw // 2
            vy = 31
            draw_fn(text, vx, vy, WHITE)

        def _fmt(v):
            if v >= 1000 and v % 1000 == 0:
                return str(int(v // 1000)) + "k"
            return str(int(v))

        draw_sm = getattr(self._d, "draw_small_text", self._d.text)
        mid_val = (min_val + max_val) / 2
        for val, yp in [(max_val, gy), (mid_val, gy + gh // 2), (min_val, gy + gh)]:
            label = _fmt(val)
            cw = int(self.CHAR_W * 0.85)
            lx = gx - len(label) * cw - 1
            ly = yp - self.CHAR_H // 2
            draw_sm(label, lx, ly, DARK)

        mid_y = gy + gh // 2
        dash, gap = 3, 3
        x = gx + 1
        while x < gx + gw:
            x2 = min(x + dash - 1, gx + gw - 1)
            self._line(x, mid_y, x2, mid_y, (51, 51, 51))
            x += dash + gap

        self._vline(gx, gy, gh + 1, DARK)
        self._hline(gx, gy + gh, gw, DARK)

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
                self._line(prev_px, prev_py, px, py, color)
            prev_px, prev_py = px, py

    def menu(self, items, selected=0, color=WHITE):
        """Draw a scrollable list menu."""
        item_h = self.CHAR_H + 6
        visible = min(len(items), (self.height - 40) // item_h)
        start = max(0, min(selected - visible // 2, len(items) - visible))
        y = 35

        for i in range(start, min(start + visible, len(items))):
            iy = y + (i - start) * item_h
            if i == selected:
                self._fill_rect(15, iy - 2, self.width - 30, item_h, DARK)
                self._d.text("> " + items[i], 18, iy, color)
            else:
                self._d.text("  " + items[i], 18, iy, GRAY)

    def compass(self, heading, color=LIGHT):
        """Draw a compass with a rotating needle."""
        cx, cy = self.center
        r = self.radius - 12

        self._draw_circle(cx, cy, r, DARK)
        self._draw_circle(cx, cy, int(r * 0.7), DARK)

        for label, angle in (("N", 0), ("E", 90), ("S", 180), ("W", 270)):
            lx = cx + int((r + 5) * math.sin(math.radians(angle)))
            ly = cy - int((r + 5) * math.cos(math.radians(angle)))
            c = WHITE if label == "N" else GRAY
            self._d.text(label, lx - self.CHAR_W // 2, ly - self.CHAR_H // 2, c)

        for angle in range(0, 360, 45):
            inner = r - 6
            outer = r
            rad = math.radians(angle)
            x1 = cx + int(inner * math.sin(rad))
            y1 = cy - int(inner * math.cos(rad))
            x2 = cx + int(outer * math.sin(rad))
            y2 = cy - int(outer * math.cos(rad))
            c = LIGHT if angle % 90 == 0 else DARK
            self._line(x1, y1, x2, y2, c)

        rad = math.radians(heading)
        needle_len = int(r * 0.85)
        half_w = 3

        nx = cx + int(needle_len * math.sin(rad))
        ny = cy - int(needle_len * math.cos(rad))
        sx = cx - int(needle_len * math.sin(rad))
        sy = cy + int(needle_len * math.cos(rad))
        px = int(half_w * math.cos(rad))
        py = int(half_w * math.sin(rad))

        self._fill_triangle(nx, ny, cx - px, cy - py, cx + px, cy + py, color)
        self._fill_triangle(sx, sy, cx - px, cy - py, cx + px, cy + py, DARK)
        self._fill_circle(cx, cy, 3, GRAY)

    def watch(self, hours, minutes, seconds=0, color=LIGHT):
        """Draw an analog watch face."""
        cx, cy = self.center
        r = self.radius - 8

        self._draw_circle(cx, cy, r, DARK)

        for i in range(12):
            angle = i * 30
            rad = math.radians(angle)
            if i % 3 == 0:
                inner = r - 8
                c = LIGHT
            else:
                inner = r - 5
                c = GRAY
            x1 = cx + int(inner * math.sin(rad))
            y1 = cy - int(inner * math.cos(rad))
            x2 = cx + int(r * math.sin(rad))
            y2 = cy - int(r * math.cos(rad))
            self._line(x1, y1, x2, y2, c)

        for num, angle in ((12, 0), (3, 90), (6, 180), (9, 270)):
            text = str(num)
            rad = math.radians(angle)
            lx = cx + int((r - 15) * math.sin(rad))
            ly = cy - int((r - 15) * math.cos(rad))
            tw = len(text) * self.CHAR_W
            self._d.text(text, lx - tw // 2, ly - self.CHAR_H // 2, WHITE)

        h_angle = (hours % 12 + minutes / 60) * 30
        h_rad = math.radians(h_angle)
        h_len = int(r * 0.50)
        h_w = 3
        hx = cx + int(h_len * math.sin(h_rad))
        hy = cy - int(h_len * math.cos(h_rad))
        px = int(h_w * math.cos(h_rad))
        py = int(h_w * math.sin(h_rad))
        self._fill_triangle(hx, hy, cx - px, cy - py, cx + px, cy + py, color)

        m_angle = (minutes + seconds / 60) * 6
        m_rad = math.radians(m_angle)
        m_len = int(r * 0.75)
        m_w = 2
        mx = cx + int(m_len * math.sin(m_rad))
        my = cy - int(m_len * math.cos(m_rad))
        px = int(m_w * math.cos(m_rad))
        py = int(m_w * math.sin(m_rad))
        self._fill_triangle(mx, my, cx - px, cy - py, cx + px, cy + py, color)

        s_angle = seconds * 6
        s_rad = math.radians(s_angle)
        s_len = int(r * 0.85)
        sx = cx + int(s_len * math.sin(s_rad))
        sy = cy - int(s_len * math.cos(s_rad))
        self._line(cx, cy, sx, sy, GRAY)
        self._fill_circle(cx, cy, 3, GRAY)

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
            scale = self.width // 16
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
                    self._fill_rect(
                        ox + col * scale, oy + row * scale, scale, scale, color
                    )

    # --- Level 2: Cardinal text & shapes ---

    def text(self, text, at="CENTER", color=WHITE, scale=1):
        """Draw text at a cardinal position or explicit (x,y)."""
        if isinstance(at, str):
            x, y = self._resolve(at, len(text), scale)
        else:
            x, y = at
        if scale > 1:
            self._draw_scaled_text(text, x, y, color, scale)
        else:
            self._d.text(text, x, y, color)

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
        """Draw a thick arc."""
        if hasattr(self._d, "draw_arc"):
            self._d.draw_arc(cx, cy, r, start_deg, sweep_deg, color, width)
            return

        arc_len = abs(math.radians(sweep_deg) * r)
        steps = max(int(arc_len * 1.5), 1)
        half_w = width // 2

        prev_points = None

        for i in range(steps + 1):
            angle = math.radians(start_deg + i * sweep_deg / steps)

            curr_points = []
            for dr in range(-half_w, half_w + 1):
                rr = r + dr
                x = round(cx + rr * math.cos(angle))
                y = round(cy + rr * math.sin(angle))
                curr_points.append((x, y))

                if prev_points is None and 0 <= x < self.width and 0 <= y < self.height:
                    self._d.pixel(x, y, color)

            if prev_points is not None:
                for (x0, y0), (x1, y1) in zip(prev_points, curr_points):
                    self._line(x0, y0, x1, y1, color)

            prev_points = curr_points

    def _draw_circle(self, cx, cy, r, color):
        """Bresenham circle."""
        x, y, d = r, 0, 1 - r
        while x >= y:
            for sx, sy in (
                (x, y),
                (y, x),
                (-x, y),
                (-y, x),
                (x, -y),
                (y, -x),
                (-x, -y),
                (-y, -x),
            ):
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
