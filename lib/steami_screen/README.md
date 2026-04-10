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

```python
import ssd1327
from machine import SPI, Pin
from steami_screen import Screen

spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)
screen = Screen(display)

screen.clear()
screen.title("STeaMi")
screen.value(42, label="Temp", unit="C")
screen.show()
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

Note: `scale=2` produces a bold effect (text drawn with 1px offset), not a true pixel-scale zoom. Backends can provide `draw_scaled_text()` for true scaling.

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
screen.bar(value=75, max_value=100)
```

---

#### Gauge

```python
screen.gauge(value=60, min_value=0, max_value=100, unit="C")
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
