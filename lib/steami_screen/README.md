# STeaMi Screen

High-level UI library for STeaMi displays.

Provides a device-agnostic abstraction layer on top of display drivers (SSD1327, GC9A01) with a simple API to draw UI elements: text layouts, widgets, menus, icons.

---

## Features

* Display abstraction (works with any FrameBuffer-based backend)
* Automatic layout for round screens (cardinal positioning, safe margins)
* Text rendering with alignment and scaling
* Drawing primitives (pixel, line, rect, circle)
* 10 widgets: title, subtitle, value, bar, gauge, graph, menu, compass, watch, face

---

## Basic Usage

On a STeaMi board, use the board-level `steami.Screen`. It picks the right display for the release (128 px grey SSD1327 on V1a/V1b, 240 px round colour GC9A01 on V1c) and offers the whole API below.

```python
from steami import Screen

screen = Screen()
screen.begin()  # allocate the frame buffer early in the program

screen.clear()
screen.title("STeaMi")
screen.value(42, label="Temp", unit="C")
screen.show()
```

To drive a display directly (any FrameBuffer-based backend):

```python
import ssd1327
from machine import SPI, Pin
from steami_screen import Screen, SSD1327Display

raw = ssd1327.WS_OLED_128X128_SPI(
    SPI(1), Pin("DATA_COMMAND_DISPLAY"), Pin("RST_DISPLAY"), Pin("CS_DISPLAY")
)
screen = Screen(SSD1327Display(raw))
```

---

## Units and Scale

The layout is designed on a 128 px screen and scaled to the real width.

| Property | 128 px (V1a/V1b) | 240 px (V1c) |
|----------|------------------|--------------|
| `screen.k` (glyph and stroke factor) | 1 | 2 |
| `screen.width`, `height` | 128 | 240 |
| `screen.center`, `radius` | (64, 64), 64 | (120, 120), 120 |

Units of the public API:

* real pixels: `pixel`, `line`, `rect`, `circle`, `text(text, at=(x, y))` (the `scale` is used as given), `arc_width`, and the properties `width`, `height`, `center`, `radius`;
* scaled by `k`: widget text and text at a cardinal position (`at="N"`, `"CENTER"`, ...);
* 128 px units: `y_offset` (for example in `bar()`).

`screen.u(v)` converts a length given in 128 px units to real pixels (`int(v * width / 128)`, so x15/8 on 240 px, not x2). Use it so that hard-coded geometry looks the same on both sizes:

```python
from steami_screen import BLACK

box_w = screen.u(56)  # 56 on 128 px, 105 on 240 px
screen.rect(screen.center[0] - box_w // 2, 10, box_w, screen.u(10), BLACK, fill=True)
```

Text grows by `k`, not by `u()`: at scale 1 a cell is 8x8 on 128 px and 8x16 on 240 px (see Fonts). Size a box that must hold text from the glyphs: `len(text) * 8 * screen.k` wide holds it on both sizes (on 240 px the text takes half of that width), and `screen.text_height()` (`8 * screen.k`) high.

---

## API Reference

### Initialization

```python
screen = Screen(display)
```

`display` must expose `fill()`, `pixel()`, `line()`, `rect()`, `fill_rect()`, `text()`, `show()`. Width and height are auto-detected from the display backend.

---

### Drawing Primitives

```python
screen.pixel(x, y, color)
screen.line(x1, y1, x2, y2, color)
screen.rect(x, y, w, h, color, fill=False)
screen.circle(x, y, r, color, fill=False)
```

---

### Text

```python
screen.text("Hello", at="CENTER")
screen.text("Top", at="N")
screen.text("Custom", at=(10, 20))
screen.text("Big", at="CENTER", scale=2)
screen.text("Été 23°C", at=(10, 20), scale=2)
```

Cardinal positions: `"N"`, `"NE"`, `"E"`, `"SE"`, `"S"`, `"SW"`, `"W"`, `"NW"`, `"CENTER"`.

`text(s, (x, y), color, scale)` is pixel text: `(x, y)` is the top left corner of the first cell, in real pixels.

* On 128 px it is the 8x8 framebuf font x `scale`.
* On 240 px it is Spleen 8x16 x `scale`, with the same pixels as Arduino's `text(s, x, y, c, scale)`. At scale 1 it is 8 px wide per character and **16 px tall**: a visible change from v0.30, which drew 8x8 cells.

Use `screen.text_height(scale)` and `screen.max_chars` (see Properties) to place it on both sizes.

On 128 px, `scale` > 1 produces a true pixel-scale zoom on SSD1327 displays via pixel-by-pixel framebuf rendering. Other backends can implement `draw_scaled_text()` for native scaling support. Backends without it fall back to a bold offset effect.

#### Fonts

The 128 px panel (V1a/V1b) draws every text in the 8x8 framebuf font, scaled by the glyph factor `f` (`k` x `scale`).

The 240 px panel (V1c) draws every text in the Spleen 2.1.0 bitmap fonts, with Arduino's cells and positions. The face depends on what the text is and on `f`:

| Text | Face on 240 px |
|------|----------------|
| Pixel text, cardinal text, title, subtitle, value unit, graph value, menu, compass and watch letters | 8x16 x `f / 2` |
| Value label, gauge labels, graph scale labels | 6x12, whatever the scale |
| Value made only of `0-9`, `+`, `-`, `.`, `:` and spaces | 16x32 x `f / 4` when `f` is a multiple of 4, else 12x24 x `f / 3` when a multiple of 3, else 8x16 x `f / 2` when even (no face otherwise) |
| Any other value (`nan`, `1e-05`, `OK`) | 8x16 x `f / 2`, like text |

In a value, the 12x24 and 16x32 faces are bold (each glyph is drawn twice, one font column apart), and `.` and `:` are narrow on every face (half a cell wide). `value()` lowers the factor until the value fits, down to `k`, and skips a factor that has no face.

Accents and other characters:

* On 240 px the accented letters (`ÀÂÄÇÈÉÊËÎÏÔÖÙÛÜàâäçèéêëîïôöùûüÿŸ`) and `°` are drawn from the font. Any other character (a control character, `"€"`, an emoji) is drawn as one `?` cell.
* On 128 px each accented letter is folded to its base letter (`é` becomes `e`) and `°` is drawn as an 8x8 degree sign. Any other character is unchanged from v0.30: framebuf draws a checkerboard for each of its UTF-8 bytes.

Kept MicroPython differences (on 240 px, compared with Arduino's `SteamiScreen`):

* The graph keeps three labels with "k" formatting, in the 6x12 face, with their rows taken from the ink edges.
* The menu keeps its fixed bar and 5 visible rows.
* The gauge fill is 2 px thicker, and the gauge outer radius is `radius - u(4)`.
* The value label is lowered when none of its characters fits.
* The margins of the cardinal positions come from the real glyph heights.
* The face cell is `width * 11 / 128`.

---

### Widgets

#### Title

```python
screen.title("STeaMi")
```

Draws text centered at the top (N position).

---

#### Subtitle

```python
screen.subtitle("Line 1", "Line 2")
```

Draws text centered at the bottom (S position). Accepts multiple lines.

---

#### Value

```python
screen.value(23.5, label="Temp", unit="C")
```

Displays a large centered value with optional label above and unit below.

---

#### Progress Bar

```python
screen.bar(75, max_val=100)
```

---

#### Gauge

```python
screen.gauge(60, min_val=0, max_val=100)
```

Draws a 270-degree arc gauge near the screen border.

---

#### Graph

```python
screen.graph([10, 20, 15, 30], min_val=0, max_val=100)
```

Draws a scrolling line graph with the last value displayed above.

With an empty list, or when the last value is NaN, the frame is drawn and the value shows `--`. With a single value, only the frame and that value are drawn. A NaN value elsewhere leaves a gap in the line: no segment reaches it, and the other points keep their place.

---

#### Menu

```python
screen.menu(["Item 1", "Item 2", "Item 3"], selected=1)
```

---

#### Compass

```python
screen.compass(heading=45)
```

Draws a compass with cardinal labels and a rotating needle.

---

#### Watch

```python
screen.watch(hours=10, minutes=30, seconds=15)
```

Draws an analog clock face.

---

#### Face

```python
screen.face("happy")
```

Draws a pixel-art expression. Available: `"happy"`, `"sad"`, `"surprised"`, `"sleeping"`, `"angry"`, `"love"`.

---

### Control

```python
screen.clear()
screen.show()
```

---

### Properties

```python
screen.center      # (64, 64) for 128x128
screen.radius      # 64 for 128x128
screen.max_chars   # 16 on 128 px, 30 on 240 px
screen.text_height(scale=1)   # 8 * scale on 128 px, 16 * scale on 240 px
```

`max_chars` is the number of text characters that fit the width at scale 1. `text_height(scale)` is the cell height of `text(s, (x, y), color, scale)` (a scale below 1 counts as 1), like Arduino's `textHeight()`.

---

## Color Constants

```python
from steami_screen import BLACK, DARK, GRAY, LIGHT, WHITE
from steami_screen import RED, GREEN, BLUE, YELLOW
```

Colors are RGB tuples. On SSD1327 they degrade to greyscale automatically.

On the GC9A01 round screen the frame holds 16 colours: each pixel is a palette index (0-15), not an RGB565 value. `GC9A01Display` maps any RGB tuple to the nearest entry of the driver palette (smallest squared RGB distance) with `steami_screen.gc9a01.rgb_to_index(color)`. A legacy int is a grey4 level: it becomes the grey `level * 17`, then the nearest palette entry, but a non-zero level never becomes black (level 1 gives the darkest grey, as it is visible on the SSD1327).

An arbitrary RGB tuple therefore shows as the nearest of the 16 palette colours (listed in the `gc9a01` README), which can surprise: `(0, 255, 0)` is nearer to the palette's dark green `(0, 128, 0)` than to `GREEN` `(119, 255, 119)`, so it shows dark green. Use the named constants, which are exact palette entries, for exact colours.

---

## GC9A01 (round colour screen)

```python
import gc9a01
from machine import SPI, Pin
from steami_screen import Screen, GC9A01Display

raw = gc9a01.GC9A01(
    SPI(1),
    Pin("DATA_COMMAND_DISPLAY"),
    Pin("CS_DISPLAY"),
    Pin("RST_DISPLAY"),
)
raw.init()
screen = Screen(GC9A01Display(raw))
```

`GC9A01Display` is 240 x 240 and has the same methods as `SSD1327Display`, including `draw_scaled_text()` for true pixel-scale 8x8 text.

It also has `draw_glyphs(fc, glyphs, n, bold, color)`, which `Screen` uses to draw the Spleen faces (see Fonts). Only the set bits of each glyph are painted, so black text and text over a coloured background (the selected menu bar, a gauge ring) keep their background. The colour is looked up once per string.

* On the gc9a01 driver, each glyph is written straight into the driver's `GS4_HMSB` frame (`raw.buffer`) by a `@micropython.viper` function, one call per glyph at any replication n, bold included (each run one column wider). Every write is clipped to the frame, so text partly off the screen draws its visible part. On the board its prototype took about 0.5 ms per 16x32 glyph, bold included, against 1.2 ms for a palette blit (2.2 ms bold).
* With another raw driver, a native face (n = 1) is blitted from the font bytes with the driver's `blit()`, through a 2x1 palette and a key, and bold blits each glyph a second time, 1 px to the right. A replicated face (n >= 2) is drawn with one `fill_rect()` per run of set bits. Both give the same pixels as the frame writer.

The font tables (`steami_screen.spleen`) are frozen in the firmware with the `steami_screen` package, so they stay in flash. They are imported on 240 px only: the 128 px path never loads them.

---

## Color Utilities

```python
from steami_screen import rgb_to_gray4, rgb_to_rgb565, rgb_to_rgb8
```

| Function | Output |
|----------|--------|
| `rgb_to_gray4(color)` | 4-bit greyscale (0-15) for SSD1327 |
| `rgb_to_rgb565(color)` | 16-bit RGB565 (a plain helper: the gc9a01 driver takes palette indexes, see `steami_screen.gc9a01.rgb_to_index`) |
| `rgb_to_rgb8(color)` | RGB tuple pass-through |

All accept int values for backward compatibility.

---

## Fonts and licence

The 240 px text uses the Spleen 2.1.0 bitmap fonts by Frederic Cambus (<https://github.com/fcambus/spleen>), faces 6x12, 8x16, 12x24 and 16x32. `steami_screen/spleen.py` was generated by `scripts/gen-spleen-fonts.py --micropython` from steamicc/arduino-steami-lib at commit [`64b8db6`](https://github.com/steamicc/arduino-steami-lib/commit/64b8db6b513de902ac30c72f7d134915bc8688bd) (main, release v0.40.0), from the same tables as the Arduino library. Regenerate it with that script, never edit it by hand.

Spleen is distributed under this notice (the LICENSE file of the release):

```text
Copyright (c) 2018-2024, Frederic Cambus
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

  * Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS
BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
```
