# SSD1327 MicroPython Driver

MicroPython driver for the **SSD1327 128x128 4-bit greyscale OLED display controller**.

This library is a port of the original MicroPython SSD1327 driver. 

## Features

* 128x128 **OLED display support**
* **4-bit greyscale** (16 levels)
* I²C and SPI interfaces
* Full **frame buffer integration**
* Drawing primitives:
  * pixels, lines, text
  * scrolling
* Display control:
  * contrast
  * invert
  * rotation
* Power management:
  * display on/off
* Optimized buffer rendering

## Display Specifications

| Feature     | Value             |
| ----------- | ----------------- |
| Resolution  | 128 × 128 pixels  |
| Color depth | 4-bit (16 levels) |
| Controller  | SSD1327           |
| Interfaces  | I²C, SPI          |

## I2C Address

Default I²C address:

```
0x3C
```

## Basic Usage

```python
from machine import I2C
from ssd1327 import WS_OLED_128X128_I2C

# Init I2C
i2c = I2C(1)

# Init display
display = WS_OLED_128X128_I2C(i2c)

# Draw
display.fill(0)
display.text("Hello STeaMi", 0, 0)

# Update screen
display.show()
```

## FrameBuffer Integration

The driver internally uses `framebuf.FrameBuffer`, meaning **all standard drawing methods are available**.

This allows you to use:

* `fill()`
* `pixel()`
* `line()`
* `rect()`
* `text()`
* `scroll()`

Example:

```python
display.line(0, 0, 127, 127, 15)
display.pixel(10, 10, 8)
display.show() # Required to update the screen
```

The buffer is stored in **4-bit greyscale format (GS4_HMSB)**. 

## API Reference

### Initialization

#### I2C

```python
SSD1327_I2C(width, height, i2c, address=0x3C)
WS_OLED_128X128_I2C(i2c, address=0x3C)
```

#### SPI

```python
SSD1327_SPI(width, height, spi, dc, res, cs)
WS_OLED_128X128_SPI(spi, dc, res, cs)
```

### Drawing Methods (FrameBuffer)

* `fill(color)`
* `pixel(x, y, color)`
* `line(x1, y1, x2, y2, color)`
* `text(string, x, y, color=15)`
* `scroll(dx, dy)`

### Display Control

* `show()` — update display with buffer
* `contrast(value)` — set brightness (0–255)
* `invert(enable)` — enable/disable inversion
* `rotate(enable)` — rotate display

### Power Management

* `power_on()` — turn display on
* `power_off()` — turn display off (low power mode)

### Low-Level

* `write_cmd(cmd)`
* `write_data(buf)`

(Implemented internally for I²C/SPI communication)

## Examples

This driver includes many examples available in the `examples/` folder:

| File           | Description        |
| -------------- | ------------------ |
| bitmap.py      | Image display      |
| framebuf_lines.py      | Draw a line      |
| framebuf_pixel.py      | Draw a pixel      |
| framebuf_rect.py      | Draw a rectangle      |
| framebuf_scroll.py      | Scroll a text      |
| framebuf_text.py      | Display a text      |
| hello_world.py      | Display "Hello World"     |
| illusion.py      | Display an optic illusion     |
| invert.py      | invert greyscale lookup table     |
| lookup_table.py      | Display gradiant     |
| micropython_logo.py      | Display micropython logo     |
| random_pixel.py      | Display random pixels     |
| rotating_3D_cube.py      | Display a rotating 3D cube     |
| rotation.py      | Rotate the 3D logo   |
| shades.py      | Display 15 shades of grey |

```bash
mpremote mount lib/ssd1327 run lib/ssd1327/examples/hello_world.py
```

## Notes

* The driver uses an internal buffer of:

```
width × height / 2 bytes
```

(4-bit per pixel)

* Display updates only occur when calling:

```python
display.show() # Required to update the screen
```

## Source

This library is a port of:
https://github.com/mcauser/micropython-ssd1327
