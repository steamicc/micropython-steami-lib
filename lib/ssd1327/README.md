# SSD1327 MicroPython Driver

MicroPython driver for the **SSD1327 128x128 4-bit greyscale OLED display controller**.

This library is a port of [micropython-ssd1327](https://github.com/mcauser/micropython-ssd1327).

## Supported Display

| Feature     | Value             |
| ----------- | ----------------- |
| Controller  | SSD1327           |
| Resolution  | 128 × 128 pixels  |
| Color depth | 4-bit (16 levels) |
| Interfaces  | I²C, SPI          |
| Default I²C address | `0x3C`   |

## Features

* 128x128 OLED display support
* 4-bit greyscale (16 levels)
* I²C and SPI interfaces
* FrameBuffer-based rendering API
* Drawing primitives: pixels, lines, text, scrolling
* Display control: contrast, invert, rotation
* Power management: display on/off

## Basic Usage

```python
from machine import I2C
from ssd1327 import WS_OLED_128X128_I2C

i2c = I2C(1)
display = WS_OLED_128X128_I2C(i2c)

display.fill(0)
display.text("Hello STeaMi", 0, 0)
display.show()
```

## FrameBuffer Integration

The driver extends `framebuf.FrameBuffer` and exposes the following drawing methods directly:

* `fill(color)` — fill entire display
* `pixel(x, y, color)` — set a single pixel
* `line(x1, y1, x2, y2, color)` — draw a line
* `text(string, x, y, color=15)` — render text
* `scroll(dx, dy)` — scroll buffer contents

Other FrameBuffer methods (`rect()`, `fill_rect()`, etc.) are accessible via `display.framebuf`.

The buffer is stored in 4-bit greyscale format (GS4_HMSB). The internal buffer uses `width × height / 2` bytes (8192 bytes for 128×128). Call `show()` to push the buffer to the display.

## API Reference

### Initialization

#### I2C (STeaMi board)

```python
from ssd1327 import WS_OLED_128X128_I2C

display = WS_OLED_128X128_I2C(i2c, address=0x3C)
```

For custom resolutions:

```python
from ssd1327 import SSD1327_I2C

display = SSD1327_I2C(width, height, i2c, address=0x3C)
```

#### SPI

```python
from ssd1327 import WS_OLED_128X128_SPI

display = WS_OLED_128X128_SPI(spi, dc, res, cs)
```

**Note:** `SSD1327_SPI` (custom resolution) is available via `from ssd1327.device import SSD1327_SPI` but is not exported by the package by default.

### Display Control

* `show()` — push the framebuffer to the display (required after any drawing)
* `contrast(value)` — set brightness (0–255)
* `invert(enable)` — enable/disable display inversion
* `rotate(enable)` — rotate display 180°

### Power Management

* `power_on()` — turn display on
* `power_off()` — turn display off (low power mode)

### SPI-only

* `reset()` — hardware reset via the reset pin (SSD1327_SPI only)

## Examples

| File                  | Description                                          |
| --------------------- | ---------------------------------------------------- |
| `bitmap.py`           | Display a 16x15 smiley bitmap with greyscale shading |
| `framebuf_lines.py`   | Draw diagonal lines across the screen                |
| `framebuf_pixels.py`  | Plot individual pixels at various positions          |
| `framebuf_rects.py`   | Draw rectangles using the FrameBuffer API            |
| `framebuf_scroll.py`  | Scroll text horizontally across the display          |
| `framebuf_text.py`    | Render text strings at different positions           |
| `hello_world.py`      | Minimal "Hello World" display example                |
| `illusion.py`         | Render an optical illusion pattern                   |
| `invert.py`           | Toggle display inversion on and off                  |
| `lookup_table.py`     | Display a greyscale gradient using all 16 levels     |
| `micropython_logo.py` | Display the MicroPython logo as a bitmap             |
| `random_pixels.py`    | Fill the screen with randomly placed pixels          |
| `rotating_3d_cube.py` | Animate a rotating wireframe 3D cube                 |
| `rotation.py`         | Demonstrate 180° display rotation                    |
| `shades.py`           | Display 15 shades of grey as vertical bands          |

```bash
mpremote mount lib/ssd1327 run lib/ssd1327/examples/hello_world.py
```
