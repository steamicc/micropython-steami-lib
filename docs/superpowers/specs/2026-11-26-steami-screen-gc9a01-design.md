# The V1c screen in MicroPython (GC9A01) — design

Status: approved on 2026-11-26.

## Intent

The STeaMi V1c has a 240×240 colour round screen, a GC9A01. The V1a and V1b have a 128×128 grey OLED, an SSD1327. In MicroPython, only the SSD1327 works today: `lib/gc9a01` is empty (issues #10, #368, #269), and every screen example builds an SSD1327 by hand. On a V1c nothing shows. The V1c is the release being deployed, so the screen examples and the samples (micropython-steami-sample) are blind on the boards that matter most.

The Arduino library solved this (`SteamiDisplay`/`SteamiScreen`, with one backend per release). This project brings the same to MicroPython: one program draws on the board's screen, whatever the release. It builds on the `steami` package (board detection and function classes, released in v0.28.2), which already reserves `display()` and the E30/E31 codes for this project.

## Goals

- A `gc9a01` driver for the V1c screen, frozen in the firmware.
- A `GC9A01Display` adapter in `steami_screen` (issue #368), the counterpart of `SSD1327Display`.
- The scaling rule agreed for both languages (maintainer's comment on #368, 2026-11-25): widgets are laid out in 128 px units and multiplied by 15/8 on the 240 px GC9A01; glyphs **and** strokes use an integer factor k = 1 on 128 px and k = 2 on 240 px, so a widget sketch looks alike on V1b and V1c. Text is really scaled on 240 px.
- A `Screen` class in `steami`: `from steami import Screen`, `screen = Screen()`. It picks the right adapter for the detected release, offers the whole `steami_screen` drawing API (title, value, subtitle, bar, gauge, graph, menu, compass, watch, face, text, line, circle, rect, pixel, clear, show), and follows the common form of the `steami` classes (`begin()`, `is_available()`, `status()`, `error()`, `chip()`).
- `Steami.display()` returns the shared adapter, as in Arduino.
- The `steami_screen` examples use `steami.Screen`, so they run on every release.

## Non-goals

- Images, gradients, photos: the colour depth is a 16-colour palette (decided with the maintainer, see Decisions).
- Rotation, inversion, power control of the panel beyond what the adapter needs. They can come later.
- Changing the driver examples that use `ssd1327` directly (radar_screen, tetris…). They are driver examples, not board examples.
- The wiki pages, and the Arduino library.

## Anti-goals

- **A regression on V1a/V1b.** The SSD1327 output of every `steami_screen` widget must stay pixel-identical (k = 1, layout unchanged at 128 px).
- **A screen that cannot coexist with BLE.** With the BLE beacon sample running, about 100 KB of heap is free: the screen must fit next to it.
- **A firmware that no longer fits.** The flash has about 3 KB free today.
- **Breaking the LPUART flash-erase fix.** No LTO and no change to the RAM-resident ISR list.

## Constraints

- RAM: the heap lives in the 192 KB SRAM1. About 125 KB is free after importing the `steami` classes, and about 100 KB with BLE running. A full RGB565 frame (115 200 bytes) does not fit next to BLE.
- Flash: about 3 KB free. The maintainer chose to drop `senml` from the frozen modules (6.3 KB, imported by no sample, no lib module and no wiki page). The GC9A01 driver and adapter are estimated at about 4 KB.
- Hardware (V1c): SPI1 ("SPIINT"): SCK PA1 and MOSI PB5. CS is `CS_DISPLAY` (PD0), D/C is `DATA_COMMAND_DISPLAY` (PB4, formerly MISO, not claimed by `SPI(1)` since `mpconfigboard.h` comments MISO out), and reset is `RST_DISPLAY` (PA12). There is no backlight pin. The SSD1327 of V1a/V1b uses the same bus and pins.
- The GC9A01 wants RGB565 high byte first. `framebuf` stores native little-endian words.
- `spi.write()` uses DMA for buffers longer than one byte, and a DMA transfer is limited to 65 535 bytes.
- MicroPython 1.29 on the firmware fork (`steamicc/micropython-steami`, branch `stm32-steami-rev1d-final`), frozen modules built with `-O3`.

## Approaches

Three ways were considered; the maintainer picked the first.

1. **A `Screen` class in `steami`, on top of `steami_screen` (picked).** The driver `gc9a01` keeps a 16-colour frame and converts it to RGB565 in strips while sending. `steami_screen` gets the adapter and the scaling rule. `steami.Screen` picks the adapter by release and exposes the `steami_screen` API, with E30/E31 messages. One program runs everywhere, the existing conventions are kept, and the examples change by one line.
2. **A factory in `steami_screen`** (`steami_screen.open()` detecting the release). A little less code, but the screen stays apart from `steami`: no coded messages, no `Steami.display()`, and the API drifts from Arduino.
3. **Port the Arduino `SteamiDisplay` to Python in `steami`.** Rejected: it duplicates `steami_screen`, which already has more widgets, and costs flash we do not have.

## Decisions

### Colour depth (maintainer)

A 16-colour palette:
- the frame is a `framebuf.FrameBuffer` in `GS4_HMSB` (240 × 240 / 2 = 28 800 bytes), each pixel being a palette index;
- `show()` converts the frame to RGB565 in strips of a few rows, through a 16-entry RGB565 lookup table, into a small reused strip buffer, and sends each strip over SPI.

**Builder's call, the palette:** the `steami_screen` named colours, then six more:
- index 0 BLACK, then GRID_DARK (51), DARK (102), GRAY (153), LIGHT (187), WHITE;
- then GREEN, RED, BLUE, YELLOW (from `steami_screen/const.py`);
- then CYAN (85, 255, 255), MAGENTA (255, 85, 255), ORANGE (255, 165, 0), DARK_GREEN (0, 128, 0), DARK_RED (128, 0, 0), DARK_BLUE (0, 0, 128).

The adapter maps an RGB tuple to its exact palette entry, or else to the nearest one (squared RGB distance), with a small cache.

### Flash (maintainer)

- Drop `senml` from the firmware manifest.
- Freeze `gc9a01` (the driver) in its place.

This is a fork PR as in v0.28.2, then a lib PR that removes `lib/gc9a01/.not-frozen`, and then a release. Measure the margin and report it.

- `steami_screen` and `steami` are already frozen, so the scaling code, the adapter and `steami.Screen` also take flash, not only the driver. Measure the frozen firmware size as soon as the driver and adapter exist, before the layout work.
- **Fallback chosen by the maintainer:** if the firmware still does not fit once `senml` is dropped, move the MicroPython filesystem up by 16 KB (`FLASH_FS` from 0x08080000 to 0x08084000, still 256 KB, ending at 0x080C4000). It stays below the largest BLE stack, which starts at 0x080CE000. The application flash grows by 16 KB.
  - The filesystem is reformatted on update. Say so in the release notes and the PR.
  - Check the linker script and the flash-storage settings of the board.
  - Check on the V1c that the filesystem works and that BLE (HCI Layer stack at 0x080E0000) still starts.

### Driver `gc9a01`

- `lib/gc9a01/gc9a01/` follows the repo layout (`device.py`, `const.py`, `manifest.py`, README, examples).
- Constructor `GC9A01(spi, dc, cs, rst=None, width=240, height=240)`. Creating it touches no hardware until `init()`/`begin()` (builder chooses the name, consistent with `ssd1327`).
- Init sequence, reset, MADCTL (including the V1c orientation) and INVON are taken from the Arduino `SteamiGC9A01.cpp` `kInitSequence`. As in Arduino, the panel RAM is cleared and sent before DISPON, so stale content never shows.
- SPI mode 0 at 16 MHz (the Arduino value on the same hardware). The builder may measure a higher speed and keep it if stable.
- The driver owns the GS4 frame and the palette lookup table, and offers the framebuf primitives the adapter needs (fill, pixel, fill_rect, rect, line, text, blit) plus `show()`.

### Adapter `steami_screen.GC9A01Display` (#368)

- Same interface as `SSD1327Display`: fill, pixel, text, line, fill_rect, rect, show, draw_scaled_text and draw_arc when useful, plus width and height (240).
- It converts RGB tuples to palette indices.
- It implements a real scaled text, `draw_scaled_text(text, x, y, color, scale)`.

### Scaling rule in `steami_screen.Screen`

**Builder's calls, taken from the Arduino implementation of the rule:** the rule was agreed for both languages, and the Arduino display design (`docs/superpowers/specs/2026-11-25-steami-display-design.md` in arduino-steami-lib, section 5.8) is its implementation. When k = 2, follow it except where it marks a MicroPython difference:
- `_resolve` margins with glyph heights in real pixels, and the floor and cap on the title row;
- gauge outer radius `radius - u(4)`;
- face cell `W * 11 / 128`.

A plain ×15/8 of today's `device.py` constants is not enough: it would give, for example, a 165 px bar instead of 200.

- `Screen` derives k from the display width: k = 1 at 128 px, k = 2 at 240 px, as Arduino's `k() = (width + 64) / 128`.
- It lays widgets out in 128 px units multiplied by width/128 (15/8 at 240 px).
- Glyphs (text and faces) and strokes are drawn with factor k.
- SSD1327 output must stay pixel-identical: a golden test captures the SSD1327 framebuffer of each widget before the change and compares after. The CPython framebuf stub draws no text, so record draw calls or extend the stub.
- **Units of the public API (builder's call, as Arduino):**
  - drawing primitives (`line`, `circle`, `rect`, `pixel`) and `text(x, y)` take real panel pixels;
  - `text(at=...)` and widget text are scaled by k;
  - `y_offset` is in 128 px units, and `arc_width` in real pixels;
  - `width`, `height`, `center` and `radius` report real pixels (240 on a V1c).
- **Round screen (builder's call, as Arduino; k = 2 only, so the SSD1327 output is unchanged):** widgets keep their text inside the circle (Arduino's truncation, title-row floor and cap, menu limited to the circle). Plain scaling would let the round edge cut "Temperature" on the title row of a V1c.

### `steami.Screen`

- Common form of the `steami` classes. The routing is SSD1327 on V1a/V1b and GC9A01 on V1c, as Arduino `steamiRoute()`.
- An unknown release gives E30 and no screen (as Arduino). Texts are copied from Arduino `SteamiDisplay.cpp`, adapted to Python as in the other classes.
- A `MemoryError` while allocating the frame gives E31: "not enough RAM for the screen (N bytes in one block). Call begin() on the Screen first in the program."
- When the screen is unavailable, drawing calls do nothing and `show()` returns quietly, the absence behaviour of the other classes.
- The drawing API is that of `steami_screen.Screen`, reached through the `Screen` object (forwarding or subclassing is the builder's call). `Screen` is lazily importable like the other classes.
- `Steami.display()` returns the shared adapter, or `None`.

### Examples and tests

- The eight `steami_screen` examples switch to `from steami import Screen`. Examples that hard-code sizes (e.g. `gauge_demo.py`, which blanks a fixed 56×10 rectangle) are adjusted to the real-pixel units, so they may change by more than one line.
- Mock tests cover:
  - the palette mapping and the RGB565 byte order of `show()`, on a fake SPI that records bytes;
  - the strip conversion;
  - the scaling rule (positions and k at 128 and 240);
  - the SSD1327 golden test;
  - routing per release, E30, E31 (simulated MemoryError), and absence.
- A hardware scenario on a V1c draws each widget and checks it does not raise. A webcam photo of the screen is attached to the PR (`/dev/video4`, see the session notes).

## Left to the builder

- The strip height and the exact SPI speed (measure the `show()` time and report it).
- How `steami.Screen` exposes the `steami_screen` API.
- The exact file split inside `gc9a01`.
- Whether `draw_arc` is worth an adapter method on GC9A01.
- The order of work and the number of PRs (driver; adapter and scaling; `steami.Screen`; firmware freeze).
