# STeaMi Board

Board detection and function classes for the STeaMi board.

The STeaMi exists in three hardware releases (V1a, V1b, V1c) whose environment
sensors differ: WSEN-HIDS, WSEN-PADS and APDS-9960 on V1a and V1b, BME280 on
V1c. Their screens differ too: a 128×128 grey SSD1327 on V1a and V1b, a
240×240 colour round GC9A01 on V1c. This package recognises the release and
gives thirteen function classes (`Temperature`, `Compass`, ...) and a `Screen`,
each of which picks the right chip. A program written with it runs unchanged
on every release.

It is the MicroPython counterpart of the Arduino library `steami_board`
(`SteamiTemperature`, `SteamiCompass`, ...), with the same names in snake_case
and without the `Steami` prefix on the function classes.

`steami.version.VERSION` holds the release of the library frozen into the
firmware (`"vX.Y.Z"`), or `"dev"` for a local build.

---

# Dependencies

The chip drivers are loaded only when a function needs them, and are the same
packages as when used alone:

* `daplink_bridge`, `steami_config` — board revision and calibrations
* `bme280`, `wsen-hids`, `wsen-pads`, `apds9960`, `vl53l1x`, `ism330dl`,
  `lis2mdl`, `bq27441`, `mcp23009e` — the chips
* `steami_screen`, `ssd1327`, `gc9a01` — the screen

The firmware freezes all of them, so `manifest.py` declares no `require()`.

---

# Basic Usage

```python
from time import sleep

from steami import Steami, Temperature

Steami.begin()               # optional: every function calls it when needed

temperature = Temperature()  # touches no hardware
if temperature.begin():
    print("Sensor:", temperature.chip())
else:
    print("No sensor:", temperature.error())

while True:
    print(temperature.read(), "C")
    sleep(1)
```

Loading is lazy: `from steami import Temperature` loads only `steami.board`,
`steami.const`, `steami.handle` and `steami.temperature`, plus the drivers the
function uses. A program only spends RAM on the functions it imports.

---

# API

Import names explicitly, for example `from steami import Temperature`:
loading is lazy, so `from steami import *` imports nothing.

Public names: `Steami`, `Release`, `Chip`, `Function`, `Status`, `Origin`,
`Vector` and the classes `Temperature`, `Humidity`, `Pressure`, `Distance`,
`Battery`, `Accelerometer`, `Gyroscope`, `Magnetometer`, `Compass`, `Light`,
`Color`, `Gesture`, `Buttons` and `Screen`.

## Steami

`Steami` is one shared object, created when `steami.board` is imported.

### Release

```python
Steami.begin()          # detect the release once, return it
Steami.begin("V1c")     # force it ("V1a", "V1b", "V1c"): no I2C traffic
Steami.release()        # Release.V1A, V1B, V1C, V1AB ("V1a/V1b") or UNKNOWN ("")
Steami.release_name()   # the release as text, "unknown" when it is not known
Steami.is_v1c()
Steami.is_v1ab()
Steami.origin()         # Origin.FORCED, CONFIG, PROBE or NONE
Steami.revision()       # the code of the board config, or None
Steami.is_prototype()
Steami.schematic_index()  # units digit of a valid revision (0 = prototype), or None
Steami.has(Function.LIGHT)   # True when this release has the function
```

`Release`, `Chip` and `Function` constants are strings equal to the Arduino
texts, so a constant and its text are interchangeable: `Release.V1C == "V1c"`.

Detection runs once, in this order, as in Arduino:

1. **Forced release**: `Steami.begin("V1c")`.
2. **Config zone**: the board revision stored in the DAPLink config zone (a
   probe checks first that the firmware has one, so old DAPLink firmwares do
   not hang). Revision codes are of the form 1xy where the release digit x is
   1, 2 or 3 (V1a, V1b, V1c), for example 131 is a V1c.
3. **I2C probing**: BME280 means V1c; WSEN-HIDS, WSEN-PADS or APDS-9960 means
   V1a/V1b (the probe cannot tell them apart).
4. Otherwise the release is unknown (E01) and the function classes try every
   candidate chip.

### Shared resources and chips

```python
Steami.i2c()            # the internal I2C bus, created on first call
Steami.config()         # a SteamiConfig, or None
Steami.claim(Chip.BME280)   # Status.OK, NOT_RESPONDING...
Steami.bme280()         # the shared driver, or None when it does not answer
# also wsen_hids(), wsen_pads(), apds9960(), vl53l1x(), ism330dl(),
# lis2mdl(), bq27441() and mcp23009e()
Steami.calibrate(Chip.LIS2MDL)
Steami.calibrated(Chip.LIS2MDL)
Steami.display()        # the shared screen adapter of steami_screen, or None
```

Each driver is created once and shared by the classes that need it. The
calibrations of the config zone are applied once per chip, on first use.

`Steami.display()` builds the screen of the release on first call, on `SPI(1)`
with the pins `CS_DISPLAY`, `DATA_COMMAND_DISPLAY` and `RST_DISPLAY`: an
`SSD1327Display` on V1a/V1b, a `GC9A01Display` on V1c. It returns `None` on an
unknown release, or when the frame does not fit in RAM; that case is tried
again on the next call. Once built, the adapter is kept until `Steami.end()`,
even if another release is forced.

### Diagnostics

```python
Steami.print_info()     # the board line, one line per chip, then the screen line
Steami.set_logger(fn)   # messages go to fn(line); None silences them
Steami.last_error()     # the last message, even when it was not printed
Steami.end()            # forget everything (release, drivers, messages, logger)
```

The screen line is `<chip> screen <state>`, as in Arduino: for example
`GC9A01 screen OK` on a V1c. The state is `not started` until the screen is
first used (`print_info()` does not start it), then `OK`, or `no memory` when
its frame did not fit in RAM. An unknown release has no screen line.

## Function classes

Every class has the same form. `begin()` is idempotent and returns `True` or
`False`; then `is_available()`, `status()`, `error()` and `chip()`. A read
before `begin()` calls `begin()`. Creating an instance touches no hardware. A
failed function is not retried until a reset. `Steami.end()` does not reset
function objects that already exist (as in Arduino): after `Steami.end()`,
create the function objects again.

| Class | Reads | Value when the function is missing |
|---|---|---|
| `Temperature` | `read()` in °C, `set_offset(c)` | `nan` |
| `Humidity` | `read()` in % RH | `nan` |
| `Pressure` | `read()` in hPa, `altitude(sea_level_hpa=1013.25)` in m | `nan` |
| `Distance` | `read()` in mm, `cm()` | `-1`, `nan` |
| `Battery` | `percent()`, `voltage()` in V, `current()` in mA, `is_charging()` | `0`, `nan`, `0`, `False` |
| `Accelerometer` | `read()` in g as a `Vector`, `x()`, `y()`, `z()`, `strength()`, `is_shaken(threshold_g=2)` | `nan`, `False` |
| `Gyroscope` | `read()` in dps as a `Vector`, `x()`, `y()`, `z()` | `nan` |
| `Magnetometer` | `read()` in µT as a `Vector`, `x()`, `y()`, `z()`, `strength()`, `calibrate(seconds=12)` | `nan` |
| `Compass` | `heading()` in degrees, `direction()`, `set_declination(deg)`, `calibrate(seconds=12)` | `nan`, `""` |
| `Light` | `read()`, the raw clear count | `0` |
| `Color` | `read()` returns `(r, g, b)`, `red()`, `green()`, `blue()`; `rgb()`, the hue with the largest channel scaled to 255 (a `steami_screen` colour) | `(0, 0, 0)`, `0` |
| `Gesture` | `read(timeout_ms=0)` returns `Gesture.NONE`, `LEFT`, `RIGHT`, `UP`, `DOWN`, `NEAR` or `FAR`; `name(g)` | `Gesture.NONE` |
| `Buttons` | `is_pressed(b)`, `was_pressed(b)`, `was_released(b)`, `wait_for_press(timeout_ms=None)` | the D-pad stays released; A, B and MENU always work |

When a vector is missing, `read()` returns `Vector(nan, nan, nan)`.

Statuses are `Status.OK`, `Status.NOT_STARTED`, `Status.NOT_RESPONDING`,
`Status.NOT_ON_THIS_BOARD`, `Status.UNKNOWN_BOARD` and, for the screen only,
`Status.NO_MEMORY`. `error()` gives `""` when OK, then `"not started"`,
`"no answer"`, `"not on this board"`, `"unknown board"` or `"no memory"`.

### Screen

```python
from steami import Screen

screen = Screen()       # touches no hardware
screen.clear()
screen.title("STeaMi")
screen.value(21.5, unit="C")
screen.show()
```

`Screen` draws on the screen of the board, whatever the release. It has the
common form (`begin()`, `is_available()`, `status()`, `error()`, `chip()`) and
the whole drawing API of `steami_screen.Screen`: `title`, `value`, `subtitle`,
`bar`, `gauge`, `graph`, `menu`, `compass`, `watch`, `face`, `text`, `line`,
`circle`, `rect`, `pixel`, `clear`, `show`, and `width`, `height`, `center`,
`radius`, `k`, `u()`. See the `steami_screen` README for the widgets and for
the scaling from 128 to 240 pixels.

`begin()`, or the first drawing call or size read, starts the shared display
(`Steami.display()`); every `Screen` draws on the same one. Without a screen,
the drawing calls do nothing and `show()` returns quietly:

* on an unknown release, the status is `Status.UNKNOWN_BOARD` (E30), and
  `width` and `height` are 128, the default size of `steami_screen`;
* when the frame does not fit in RAM (28 800 bytes in one block on V1c, 8 192
  on V1a/V1b), the status is `Status.NO_MEMORY` (E31), `chip()` still names
  the panel, and `width` and `height` are its size. Call `begin()` on the `Screen` first
  in the program, before the heap is fragmented: creating it allocates
  nothing, `begin()` (or the first drawing call) allocates the frame.

### Routing

Each function uses the chip of this table, the same as Arduino. V1a and V1b are
routed identically.

| Function | V1a / V1b | V1c | Unknown release |
|---|---|---|---|
| Temperature | WSEN-HIDS, then WSEN-PADS | BME280 | BME280, WSEN-HIDS, WSEN-PADS |
| Humidity | WSEN-HIDS | BME280 | BME280, WSEN-HIDS |
| Pressure | WSEN-PADS | BME280 | BME280, WSEN-PADS |
| Light, Color, Gesture | APDS-9960 | none (E20) | APDS-9960 |
| Distance | VL53L1X | VL53L1X | VL53L1X |
| Accelerometer, Gyroscope | ISM330DL | ISM330DL | ISM330DL |
| Magnetometer, Compass | LIS2MDL | LIS2MDL | LIS2MDL |
| Battery | BQ27441 | BQ27441 | BQ27441 |
| Buttons | A, B, MENU on the MCU; D-pad on MCP23009E | same | same |
| Screen | SSD1327 | GC9A01 | none (E30) |

### Calibration

The calibrations of the DAPLink config zone (`tc`, `cm`, `ca`; see
`steami_config`) are applied automatically, once per chip, on first use, even
when the release is forced. For the WSEN-HIDS, the `tc.hid` key is used like in
Arduino, or `tc.hts` when `tc.hid` is missing or is the identity (the key that
older versions of `steami_config/examples/calibrate_temperature.py` wrote,
through the removed HTS221 driver; the current tool removes it). Arduino reads
it the same way (steamicc/arduino-steami-lib#301).

## Buzzer

```python
from steami import tone, no_tone

tone(440)        # A4 until no_tone() or the next tone()
tone(880, 200)   # stops by itself after 200 ms, without blocking
no_tone()
```

`tone(frequency, duration_ms=0)` and `no_tone()` mirror Arduino `tone()` and
`noTone()`: a 50 % square wave on `SPEAKER` (PA11), Timer 1 channel 4, created
on first call. A frequency of 0 or less silences the buzzer. The timed stop
uses a one-shot soft `machine.Timer`.

## Pads on the expander

The crocodile pads P28, P29, P24 and P25 are GPIO 0 to 3 of the MCP23009E, not
pins of the MCU. `PAD_P28`, `PAD_P29`, `PAD_P24` and `PAD_P25` give their GPIO
number, for `MCP23009Pin`:

```python
from mcp23009e import MCP23009Pin
from steami import PAD_P24, Steami

pad = MCP23009Pin(Steami.mcp23009e(), PAD_P24, MCP23009Pin.IN, MCP23009Pin.PULL_UP)
pad.value()
```

The expander outputs are open-drain: they sink current (25 mA at most per pin)
but do not source it. Wire a load such as an LED from 3V3 to the pad and drive
the pad to 0 to turn it on.

---

# Messages

Problems are reported with the same short coded lines as Arduino, each
(who, code) pair once, through `print` by default:

```
[STeaMi] Board V1c (read from the board config, revision 131)
[STeaMi] Light: this STeaMi is a V1c, it has no light sensor (APDS-9960 is on V1a/V1b only). read() will return 0. (E20)
```

| Code | Meaning |
|---|---|
| E01 | Unknown board: no sensor answered, so the release is unknown |
| E02 | Unknown board revision code in the board config |
| E10 | A chip did not answer |
| E11 | The release (forced or from the config) is contradicted by a chip that does not answer |
| E20 | The function is not on this release |
| E30 | Unknown board: the screen cannot be chosen |
| E31 | Not enough RAM for the screen frame |

Board-level messages are signed `SteamiBoard`; function messages are signed
with the Python class name (`Light`, `Temperature`...).

There is no E03 (no `#define`).
`Steami.set_logger(fn)` redirects the lines, `Steami.set_logger(None)`
silences them, and `Steami.last_error()` returns the last one.

---

# Differences from Arduino

* Messages name the Python class (`Temperature`, not `SteamiTemperature`), and
  the advice for a forced release is `Steami.begin("V1c")`.
* `Steami.begin("V1c")` replaces the `#define STEAMI_BOARD_V1C` of Arduino: so
  there is no E03.
* Three-axis reads return a `Vector` namedtuple with fields `x`, `y`, `z`,
  instead of `SteamiVector`.
* `Color.read()` returns a tuple, because Python has no output arguments.
  Arduino's boolean result is replaced by `is_available()`. `Color.rgb()`
  returns a tuple `(r, g, b)` (a `steami_screen` colour) instead of
  `SteamiRgb`, and `(0, 0, 0)` where Arduino returns `STEAMI_BLACK`.
* `Steami.revision()` and `Steami.schematic_index()` return `None` when there
  is no valid revision, where Arduino returns -1 and 0xFF.
* `Gesture.read()` returns a text (`Gesture.RIGHT == "RIGHT"`), where Arduino
  returns a `SteamiGesture::Direction` value.
* Buttons are named by strings: `"A"`, `"B"`, `"MENU"`, `"UP"`, `"DOWN"`,
  `"LEFT"`, `"RIGHT"`. Any other name raises `ValueError`, where Arduino
  returns false for `SteamiButton::NONE`.
* `Buttons.wait_for_press(None)` waits forever. `wait_for_press(0)` does not
  wait: it samples, drops the presses found, samples again and returns `None`
  unless a press came between the two samples. Arduino uses 0 for "forever".
* Debounce is the Arduino 20 ms lock-out: a change is taken at once, then the
  bounces of the next 20 ms are ignored. As in Arduino, a tap made between
  two calls is not missed. A, B and MENU get a hard IRQ on both edges
  (`Pin.irq(hard=True)`, EXTI lines 7, 8 and 0): a tap between two calls
  gives `was_pressed()` and `was_released()` at the next call. The D-pad has
  no MCU interrupt (`INT_EXPANDER`, PB0, shares EXTI line 0 with MENU, PA0):
  each call reads the latch of the MCP23009E (`interrupt_event()`), so a tap
  gives `was_pressed()` and `is_pressed()` at the next call and the release
  one call later (20 ms with no change on that button). At most one press
  per button is reported between two calls. With several `Buttons` objects,
  those taps go to the one started or called last; every object follows the
  levels of all the buttons.
* `Buttons` cannot share EXTI line 0 with
  `MCP23009E(interrupt_pin=Pin("INT_EXPANDER"))`, as in the mcp23009e
  examples `reaction_timer.py` and `sleep_on_button.py`: when the line is
  already taken, MENU is only sampled at each call; when `Buttons` took it
  first, the later `Pin.irq()` raises `OSError`. Pad callbacks set with
  `Steami.mcp23009e().interrupt_on_*()` are still called, by every
  `Buttons` call. As in Arduino, such a callback cannot stop `Buttons`: an
  exception it raises is printed (`sys.print_exception()`, as for an IRQ
  handler) and the call returns its result. `interrupt_event()` called by
  the program itself still raises it.
* `Steami.end()` also resets the logger to `print`; Arduino keeps it.
* `tone(frequency, duration_ms)` takes no pin: the board has one buzzer.
  Arduino calls `tone(SPEAKER, frequency, duration)`.
* The pad constants are `PAD_P24`... where Arduino has `STEAMI_PAD_P24`...
* `Steami.begin()` returns the release text (truthy when the release is
  known) where Arduino returns a bool.
* Statuses are class constants (`Status.OK`, ...).
* `Steami.config()` loads the config zone on demand, on its first call.
  Arduino's `config()` returns `nullptr` until detection or `calibrate()` has
  loaded it.
* `Steami.print_info()` sends its lines through the logger only (see
  `set_logger()`); there is no `printInfo(Print& out)` with an output
  argument.
* `Screen` is `SteamiScreen`, with the `steami_screen` widgets. Its frame is
  16 colours (28 800 bytes on V1c) instead of RGB565 (115 200 bytes), so E31
  gives that size.
* On an unknown release, `width` and `height` are 128 (the default size of
  `steami_screen`), where Arduino gives 0: the widgets need a size to lay
  out. When the frame does not fit in RAM, both give the panel's size.
* A screen that did not fit in RAM is tried again by the next `begin()` of a
  new `Screen` or by `Steami.display()`; Arduino keeps the failure until
  `Steami.end()`.

---

# Examples

| Example | Description |
| ------- | ----------- |
| `board_info.py` | Print the release, where it comes from, and the state of each chip |
| `temperature.py`, `humidity.py`, `pressure.py` | Environment sensors, on every release |
| `distance.py`, `battery.py` | Distance in mm and battery charge, voltage and current |
| `accelerometer.py`, `gyroscope.py`, `magnetometer.py` | Motion and magnetic field, as vectors |
| `compass.py` | Heading and direction, with a calibration on MENU |
| `light.py`, `color.py`, `gesture.py` | APDS-9960, V1a and V1b only |
| `buttons.py` | Press and release of the seven buttons |
| `weather_station.py` | Temperature, humidity, pressure graph and compass on four screen pages, changed with the buttons (and a swipe on V1a/V1b) |
| `pads.py` | Read a crocodile pad and drive another one, on the expander |

---

# Tests

```bash
python -m pytest tests/ -k mock
```
