# GC9A01 MicroPython Driver

MicroPython driver for the **GC9A01 240x240 round colour TFT controller**, the screen of the STeaMi V1c.

The init sequence, the reset timing and the V1c orientation come from the Arduino driver `SteamiGC9A01` of [arduino-steami-lib](https://github.com/steamicc/arduino-steami-lib).

## Supported Display

| Feature     | Value                                   |
| ----------- | --------------------------------------- |
| Controller  | GC9A01                                  |
| Resolution  | 240 × 240 pixels (round)                |
| Panel colour | RGB565 (65 536 colours)                |
| Frame colour | 16-colour palette (4 bits per pixel)   |
| Interface   | SPI, mode 0 at 32 MHz                   |

## Features

* 16-colour frame of 28 800 bytes: a full RGB565 frame (115 200 bytes) does not fit next to BLE
* RGB565 conversion while sending, a few rows at a time
* FrameBuffer drawing primitives: pixels, lines, rectangles, text, blit
* Panel RAM cleared before the display turns on, so no stale content shows at boot
* Power management: display on/off

## Wiring (STeaMi V1c)

| Signal | STeaMi pin                       |
| ------ | -------------------------------- |
| SCK    | PA1 (`SPI(1)`)                   |
| MOSI   | PB5 (`SPI(1)`)                   |
| CS     | `Pin("CS_DISPLAY")` (PD0)        |
| D/C    | `Pin("DATA_COMMAND_DISPLAY")` (PB4) |
| Reset  | `Pin("RST_DISPLAY")` (PA12)      |

There is no backlight pin: the backlight is always on.

## Basic Usage

```python
from machine import SPI, Pin
from gc9a01 import GC9A01

spi = SPI(1)
display = GC9A01(
    spi,
    Pin("DATA_COMMAND_DISPLAY"),
    Pin("CS_DISPLAY"),
    Pin("RST_DISPLAY"),
)
display.init()

display.fill(0)
display.text("Hello STeaMi", 72, 116, 5)
display.show()
```

## Palette

Colours are palette indexes (0 to 15), not RGB values. The palette is `gc9a01.PALETTE`:

| Index | Name       | RGB             |
| ----- | ---------- | --------------- |
| 0     | BLACK      | (0, 0, 0)       |
| 1     | GRID_DARK  | (51, 51, 51)    |
| 2     | DARK       | (102, 102, 102) |
| 3     | GRAY       | (153, 153, 153) |
| 4     | LIGHT      | (187, 187, 187) |
| 5     | WHITE      | (255, 255, 255) |
| 6     | GREEN      | (119, 255, 119) |
| 7     | RED        | (255, 85, 85)   |
| 8     | BLUE       | (85, 85, 255)   |
| 9     | YELLOW     | (255, 255, 85)  |
| 10    | CYAN       | (85, 255, 255)  |
| 11    | MAGENTA    | (255, 85, 255)  |
| 12    | ORANGE     | (255, 165, 0)   |
| 13    | DARK_GREEN | (0, 128, 0)     |
| 14    | DARK_RED   | (128, 0, 0)     |
| 15    | DARK_BLUE  | (0, 0, 128)     |

`gc9a01.PALETTE_RGB565` holds the same colours in RGB565, byte-swapped so that `framebuf` (little-endian words) stores them high byte first, as the panel reads them.

## Memory

| Buffer           | Size         |
| ---------------- | ------------ |
| Frame (GS4_HMSB) | 28 800 bytes |
| RGB565 strip (16 rows) | 7 680 bytes |
| Palette (RGB565) | 32 bytes     |

All buffers are allocated by the constructor, so a lack of RAM shows up when the object is created. Create the display early in the program, before the heap gets fragmented.

`show()` converts 16 rows at a time into the strip buffer and sends each strip over SPI (15 writes of 7 680 bytes; each write stays under the 65 535-byte DMA limit). CS stays low for the whole frame.

The conversion is a `@micropython.viper` function that looks up the RGB565 word of each pixel in the palette and writes it into the strip. The bytes are the same as with the `FrameBuffer.blit()` through a palette it replaced. Measured on the V1c (STM32WB55 at 64 MHz, MicroPython 1.29), per strip of 16 rows:

| Step                              | Time   |
| --------------------------------- | ------ |
| Conversion, viper                 | 3.6 ms |
| Conversion, palette blit (before) | 7.1 ms |
| SPI write at 16 MHz (before)      | 3.9 ms |
| SPI write at 32 MHz               | 2.0 ms |

A whole `show()` took 167 ms with the blit at 16 MHz and takes 74 ms with the viper conversion at 32 MHz, measured on the V1c (15 strips of 3.6 + 2.0 ms add up to 84 ms; the board measured less).

The SPI clock is `BAUDRATE` in `gc9a01/const.py`: 32 MHz, the SPI1 maximum on the STeaMi (64 MHz PCLK2 / 2), checked on a V1c (identical pixels under a webcam, all V1c hardware tests pass). If a panel shows errors at that speed, set it back to 16 MHz (`16_000_000`), the speed used before.

## API Reference

### Initialization

```python
display = GC9A01(spi, dc, cs, rst=None, width=240, height=240)
```

Creating the object touches no pin and no bus.

* `init()` — reset the panel (`reset()` with `rst`, `soft_reset()` without), send the init sequence, clear the screen, then turn the display on

### Reset

As for the other drivers of this library, `reset()` is the hardware reset and `soft_reset()` the software one:

* `reset()` — pulse the `rst` pin (10 ms high, 10 ms low, then high), then wait 120 ms; raises `ValueError` when the object has no `rst` pin
* `soft_reset()` — send the software reset command (SWRESET), then wait 120 ms

Both leave the controller asleep with its default registers: call `init()` to use the screen again.

### Drawing

Coordinates are in pixels; drawing outside the screen is clipped.

* `fill(i)` — fill the whole frame
* `pixel(x, y, i=None)` — set a pixel, or return its index when `i` is omitted
* `fill_rect(x, y, w, h, i)` — draw a filled rectangle
* `rect(x, y, w, h, i)` — draw a rectangle outline
* `line(x1, y1, x2, y2, i)` — draw a line
* `text(s, x, y, i)` — draw text with the 8x8 framebuf font
* `blit(fb, x, y, key=-1, palette=None)` — copy a FrameBuffer, or a read-only `(buffer, w, h, format)` tuple; with a palette each source pixel is mapped through it before the key test; pixels equal to `key` are skipped

The GS4_HMSB FrameBuffer itself is `display.framebuf`, for the other FrameBuffer methods (`ellipse()`, `poly()`, `scroll()`...).

### Display Control

* `show()` — send the frame to the screen (required after drawing)

`show()` takes about 74 ms (see Memory) and is not synchronised with the panel refresh: the tearing-effect (TE) output of the GC9A01 is not wired on the STeaMi V1c, so a fast animation can tear.

### Power Management

* `power_off()` — turn the display off and put the controller to sleep
* `power_on()` — wake the controller and turn the display on

## Examples

| File         | Description                                  |
| ------------ | -------------------------------------------- |
| `palette.py` | Show the 16 palette colours as a 4 x 4 grid  |

```bash
mpremote mount lib/gc9a01 run lib/gc9a01/examples/palette.py
```
