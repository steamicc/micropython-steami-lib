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

`screen.u(v)` converts a length given in 128 px units to real pixels (`int(v * width / 128)`). Use it so that hard-coded geometry looks the same on both sizes:

```python
box_w = screen.u(56)  # 56 on 128 px, 112 on 240 px
screen.rect(screen.center[0] - box_w // 2, 10, box_w, screen.u(10), BLACK, fill=True)
```

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
```

Cardinal positions: `"N"`, `"NE"`, `"E"`, `"SE"`, `"S"`, `"SW"`, `"W"`, `"NW"`, `"CENTER"`.

Note: `scale` > 1 produces a true pixel-scale zoom on SSD1327 displays via pixel-by-pixel framebuf rendering. Other backends can implement `draw_scaled_text()` for native scaling support. Backends without it fall back to a bold offset effect.

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
screen.max_chars   # 16 for 128px width
```

---

## Color Constants

```python
from steami_screen import BLACK, DARK, GRAY, LIGHT, WHITE
from steami_screen import RED, GREEN, BLUE, YELLOW
```

Colors are RGB tuples. On SSD1327 they degrade to greyscale automatically.

On the GC9A01 round screen the frame holds 16 colours. `GC9A01Display` maps any RGB tuple to the nearest entry of the driver palette (smallest squared RGB distance) with `rgb_to_index(color)`. A legacy int is a grey4 level: it becomes the grey `level * 17`, then the nearest palette entry.

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

`GC9A01Display` is 240 x 240 and has the same methods as `SSD1327Display`, including `draw_scaled_text()` for true pixel-scale text.

---

## Color Utilities

```python
from steami_screen import rgb_to_gray4, rgb_to_rgb565, rgb_to_rgb8
```

| Function | Output |
|----------|--------|
| `rgb_to_gray4(color)` | 4-bit greyscale (0-15) for SSD1327 |
| `rgb_to_rgb565(color)` | 16-bit RGB565 for GC9A01 |
| `rgb_to_rgb8(color)` | RGB tuple pass-through |

All accept int values for backward compatibility.
