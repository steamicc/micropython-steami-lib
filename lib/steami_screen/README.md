# STeaMi Screen MicroPython Driver

High-level UI and drawing library for STeaMi displays.

This driver provides a **device-agnostic abstraction layer** on top of display drivers
(SSD1327, GC9A01, etc.) and exposes a **simple API to draw UI elements** such as:

- text layouts
- widgets (bars, gauges, graphs)
- menus
- icons and faces

It is designed to make building **embedded UIs fast and consistent**.

---

## Features

* Display abstraction (works with multiple backends)
* Automatic layout helpers (center, north, etc.)
* Text rendering with alignment and scaling
* Basic drawing primitives (pixel, line, rect, circle)
* UI components:
  * title / subtitle / value blocks
  * progress bar
  * menu rendering
  * graph plotting
  * gauge display
  * compass
  * watch (clock UI)
  * face / icon rendering
* Backend delegation (compatible with FrameBuffer-based drivers)
* Mock-testable architecture (no hardware required)

---

## Supported Backends

The driver works with any display exposing a FrameBuffer-like API:

- `fill()`
- `pixel()`
- `line()`
- `rect()` / `fill_rect()`
- `text()`
- `show()`

Tested with:

- SSD1327 (OLED 128x128)
- GC9A01 (round TFT)

---

## Basic Usage

```python
import ssd1327
from machine import I2C, SPI, Pin
from steami_screen import Screen, SSD1327Display

spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

raw_display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)
display = SSD1327Display(raw_display)
screen = Screen(display)

screen.clear()
screen.title("STeaMi")
screen.value(42, label="Temp", unit="C")
screen.show()
```

---

## API Reference

## Initialization

```python
screen = Screen(display)
```

* `display`: backend display driver (SSD1327, GC9A01, etc.)

---

## Core Methods

### Clear screen

```python
screen.clear()
```

Fill the screen with background color.

---

### Update display

```python
screen.show()
```

Push buffer to display.

---

## Drawing Primitives

### Pixel

```python
screen.pixel(x, y, color)
```

---

### Line

```python
screen.line(x1, y1, x2, y2, color)
```

---

### Rectangle

```python
screen.rect(x, y, w, h, color)
screen.rect(x, y, w, h, color, fill=True)
```

---

### Circle

```python
screen.circle(x, y, r, color)
screen.circle(x, y, r, color, fill=True)
```

---

## Text Rendering

### Basic text

```python
screen.text("Hello", at=(x, y))
```

---

### Positioned text

```python
screen.text("Centered", at="CENTER")
```

Supported positions:

* `"CENTER"`
* `"N"`
* `"S"`
* `"E"`
* `"W"`

Invalid values fallback to center.

---

### Scaled text

```python
screen.text("Big", at=(x, y), scale=2)
```

The fallback implementation does not perform true pixel scaling. Instead, it draws the same text multiple times with a 1px offset, creating a "bold" effect rather than a real ×2 scale.

---

## Layout Helpers

### Title

```python
screen.title("Title")
```

Draws text near the top (NORTH).

---

### Subtitle

```python
screen.subtitle("Line 1", "Line 2")
```

Supports multiple lines.

---

### Value

```python
screen.value(23.5, label="Temp", unit="C")
```

Displays a main value with optional label and unit.

---

## Widgets

### Progress Bar

```python
screen.bar(value=75, max_value=100)
```

---

### Menu

```python
screen.menu(["Item 1", "Item 2", "Item 3"], selected=1)
```

---

### Face / Icon

```python
screen.face("happy")
```

Supports predefined expressions or custom bitmaps.

---

### Graph

```python
screen.graph([10, 20, 15, 30])
```

Draws a simple line graph.

---

### Gauge

```python
screen.gauge(value=60, min_value=0, max_value=100)
```

---

### Compass

```python
screen.compass(angle=45)
```

Displays a compass with direction labels.

---

### Watch (Clock)

```python
screen.watch(hours=10, minutes=30)
```

Draws an analog-style clock.

---

## Examples

| Example       | Description                |
| ------------- | -------------------------- |
| `watch.py`    | Analog clock display       |

Run with:

```bash
mpremote mount lib/steami_screen run lib/steami_screen/examples/watch.py
```

---

## Design Notes

* The driver **does not depend on a specific display**
* All drawing is delegated to the backend (`display`)
* Layout logic is handled in `Screen`
* Optimized for **readability over raw performance**
