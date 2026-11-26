# Board detection and function classes for MicroPython — design

Status: waiting for approval.

## Intent

The STeaMi board exists in three hardware releases: V1a, V1b and V1c. The environment sensors differ between releases: WSEN-HIDS, WSEN-PADS and APDS-9960 on V1a and V1b, BME280 on V1c. So a MicroPython program written for one release does not work on another. The same is true of the samples in micropython-steami-sample and of the wiki examples. A test on a V1c (2026-11-26) confirmed that the current samples are tied to the release they were written for.

The Arduino library (steamicc/arduino-steami-lib, `lib/steami_board`) solved this with a `Steami` object, which recognises the release, and thirteen "function classes" (`SteamiTemperature`, `SteamiCompass`…), each of which picks the right chip. This project brings the same thing to micropython-steami-lib, so that one MicroPython program runs unchanged on every release.

The Python API mirrors the Arduino one, with the same class and method names in snake_case (chosen by the maintainer). A teacher can then switch between the two languages without relearning, and the wiki can show both side by side.

## Goals

- Recognise the board release automatically, in the same order and with the same results as the Arduino library.
- Offer thirteen function classes: `Temperature`, `Humidity`, `Pressure`, `Distance`, `Battery`, `Accelerometer`, `Gyroscope`, `Magnetometer`, `Compass`, `Light`, `Color`, `Gesture` and `Buttons`. Each one uses the chip that serves its function on the detected release.
- Create each chip driver once and share it between the classes that need it (for example the ISM330DL for `Accelerometer` and `Gyroscope`).
- Apply the calibrations stored in the DAPLink config zone automatically, once per chip.
- Report problems with the same short coded messages as Arduino (`[STeaMi] <who>: <detail> (Exx)`), each one printed once.
- Freeze the package in the STeaMi MicroPython firmware.

## Non-goals

- **The screen.** There is no `Screen` or `Display` class here, and no GC9A01 driver. That is a second project: the GC9A01 driver (issue #368), then screen routing in `steami_screen`. This project must not block it: `Steami` keeps a place for `display()` later.
- Rewriting the existing chip drivers. They stay usable on their own, as today.
- A wiki page for the MicroPython classes. It comes after this project, mirroring the Arduino page "Reconnaître la carte".
- Changing the Arduino library.

## Anti-goals

These would make the project a failure even if it works:

- `import steami` costs enough RAM that a small student program no longer fits. Loading has to stay lazy (see Approaches). The acceptance criterion, chosen by the maintainer: the BLE samples of micropython-steami-sample, the heaviest in memory because of aioble, must keep running once they use `steami`. The RAM cost is measured on the board and reported in the pull request.
- A program that runs on a board with an old DAPLink firmware hangs at start-up. The config-zone check must protect it, as in Arduino.
- The Python names or behaviours diverge from Arduino for no reason. When they have to differ, the difference is written down (see Decisions).
- The existing drivers or their tests break.

## Constraints

- STM32WB55: 192 KB of SRAM1, shared with the MicroPython heap and BLE. Every frozen module costs flash, and every import costs heap.
- The firmware is MicroPython v1.29.0 from our fork (`steamicc/micropython-steami`, branch `stm32-steami-rev1d-final`), built at the `EXTRA_FEATURES` level. Module-level `__getattr__` (`MICROPY_MODULE_GETATTR`) is enabled there.
- Library conventions (CONTRIBUTING.md): one package per directory under `lib/` with `manifest.py`, `README.md` and `examples/`, and snake_case enforced by ruff. Drivers do not `print()`. The board layer is an exception: like Arduino, it is user-facing and prints its messages, through a replaceable logger.
- `tests/test_frozen_manifest.py`: every `lib/*` directory must be `require`d in the firmware manifest or carry a `.not-frozen` marker.
- Mock tests are mandatory (TESTING.md). The current `FakeI2C` only accepts one address, so probing several chips needs a multi-address fake.
- Old DAPLink firmwares lock up on config commands. Arduino probes first with a READ_SECTOR (0x20) of sector 0 (`SteamiDaplinkBridge::hasConfigZone()`). The MicroPython `daplink_bridge` has no such probe yet.
- Pins: `A_BUTTON` (PA7), `B_BUTTON` (PA8) and `MENU_BUTTON` (PA0) are on the MCU. The D-pad is on the MCP23009E.

## Approaches

Three ways were considered; the maintainer picked the first.

1. **A `steami` package split into lazily loaded modules (picked).** `lib/steami/` holds `board.py` (release detection, driver cache, calibration, messages) and one small module per function (`temperature.py`, `compass.py`…). `steami/__init__.py` uses a module-level `__getattr__`, so `from steami import Temperature` loads only `board.py`, `temperature.py` and the drivers they use. The routing table is a plain dict. Pros: RAM is spent only on the functions a program uses, and the layout matches the Arduino one (one class per file). Cons: more files.
2. **A single `steami.py` module.** Simpler to read and to freeze, but importing it loads every class. That works against small student programs.
3. **Put the logic inside each driver** (a common `read()` in `bme280`, `wsen_hids`…). Rejected: no central release detection, no shared messages, and every driver would depend on the board.

## Decisions

### Naming releases, functions and chips (builder's call)

Class constants whose values are the Arduino texts, so that a constant and its string are interchangeable:

- `Release.V1A == "V1a"`, `Release.V1B == "V1b"`, `Release.V1C == "V1c"`, `Release.V1AB == "V1a/V1b"` (the result of probing, which cannot tell V1a from V1b) and `Release.UNKNOWN == ""`. `Steami.release()` returns one of them, and `Steami.begin()` accepts a constant or its string.
- `Chip.BME280 == "BME280"`, `Chip.WSEN_HIDS == "WSEN-HIDS"`… with the same texts as Arduino's `chip()`. `claim()`, `calibrate()` and `calibrated()` take them.
- `Function.TEMPERATURE == "temperature"`… for `has()`.

### Package and import

- Package `steami` in `lib/steami/`, with `manifest.py` and `README.md`, plus one example per class in `examples/` (as in Arduino: Temperature, Humidity, …, Buttons, and BoardInfo).
- `from steami import Steami, Temperature, Compass, ...` works, and loads only what is named.
- `Steami` is a single shared instance created at import of `steami.board`, like Arduino's global `Steami`.

### Release detection

`Steami.begin()` runs detection once, in this order, the same as Arduino:

1. **Forced release.** `Steami.begin("V1c")` (also `"V1a"`, `"V1b"`) skips detection, with no I2C traffic. There is no equivalent of Arduino's `#define` registrar, and so no E03.
2. **Config zone.** If `daplink_bridge` confirms the zone exists (new probe, see below), read `rev` through `steami_config`. Decode it the same way as `steamiDecodeRevision`: an integer from 100 to 999, generation 1, release digit 1, 2 or 3 → V1a, V1b or V1c, units digit 0 → prototype. An invalid code gives E02 and falls through to probing.
3. **I2C probing**, with the same table as Arduino: BME280 (0xD0 = 0x60) → V1c; WSEN-HIDS (0x0F = 0xBC), WSEN-PADS (0x0F = 0xB3) or APDS-9960 (0x92 ∈ {0xAB, 0x9C, 0xA8}) → V1a/V1b.
4. Otherwise, the release is unknown (E01), and the function classes try every candidate chip.

The origin (forced, config, probe, none) is kept and shown in the banner line: `[STeaMi] Board V1c (read from the board config, revision 131)`, the same texts as Arduino.

### Routing

The same table as Arduino (`steamiRoute()`). V1a and V1b are routed identically:

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

### The `Steami` object

The Arduino methods in snake_case:

- Release: `begin(release=None)`, `release()`, `release_name()`, `is_v1c()`, `is_v1ab()`, `origin()`, `revision()`, `is_prototype()` and `has(function)`.
- Shared resources: `i2c()`, the internal I2C bus, created on first call; `config()`, a `SteamiConfig` instance or `None`.
- Chips: `claim(chip)` returns the status, and the accessors `bme280()`, `wsen_hids()`, `wsen_pads()`, `apds9960()`, `vl53l1x()`, `ism330dl()`, `lis2mdl()`, `bq27441()` and `mcp23009e()` return the shared driver, or `None` if the chip does not answer.
- Calibration: `calibrate(chip)` and `calibrated(chip)`.
- Diagnostics: `print_info()`, `set_logger(fn)` and `last_error()`.

### The function classes

Common form, as in Arduino: `begin()` is idempotent and returns `True`/`False`. Then `is_available()`, `status()`, `error()` and `chip()`. A read before `begin()` calls `begin()`. Creating an instance does not touch the hardware. A failed function is not retried before a reset.

Reads and absence values follow the Arduino table, in snake_case:

| Class | Reads | Value when the function is missing |
|---|---|---|
| `Temperature` | `read()` in °C, `set_offset()` | `nan` |
| `Humidity` | `read()` in % RH | `nan` |
| `Pressure` | `read()` in hPa, `altitude(sea_level_hpa=1013.25)` in m | `nan` |
| `Distance` | `read()` in mm, `cm()` | `-1`, `nan` |
| `Battery` | `percent()`, `voltage()` in V, `current()` in mA, `is_charging()` | `0`, `nan`, `0`, `False` |
| `Accelerometer` | `read()` in g as a vector, `x()`, `y()`, `z()`, `strength()`, `is_shaken(threshold_g=2)` | `nan`, `False` |
| `Gyroscope` | `read()` in dps as a vector, `x()`, `y()`, `z()` | `nan` |
| `Magnetometer` | `read()` in µT as a vector, `x()`, `y()`, `z()`, `strength()`, `calibrate()` | `nan` |
| `Compass` | `heading()` in degrees, `direction()`, `set_declination()`, `calibrate()` | `nan`, `""` |
| `Light` | `read()`, raw sensor count | `0` |
| `Color` | `read()` → `(r, g, b)`, `red()`, `green()`, `blue()` | `(0, 0, 0)`, `0` |
| `Gesture` | `read(timeout_ms)` → a gesture constant, `name()` | `Gesture.NONE` |
| `Buttons` | `is_pressed(b)`, `was_pressed(b)`, `was_released(b)`, `wait_for_press()` | D-pad stays released; A, B and MENU always work |

Where Python differs from Arduino (builder's calls, listed for the maintainer to check):

- The three-axis reads return a `Vector` namedtuple with fields `x`, `y`, `z`, instead of `SteamiVector`.
- `Color.read()` returns a tuple, because Python has no output arguments. Arduino's boolean result is replaced by `is_available()`.
- Buttons are named by strings: `"A"`, `"B"`, `"MENU"`, `"UP"`, `"DOWN"`, `"LEFT"`, `"RIGHT"`. Debounce is 20 ms, as in Arduino.
- Statuses are class constants (`Status.OK`, `Status.NOT_RESPONDING`, `Status.NOT_ON_THIS_BOARD`, `Status.NOT_STARTED`). The `error()` texts are those of Arduino.
- Accelerometer settings on `begin()`: ±8 g at 104 Hz, as in Arduino.

### Messages

- Same format and codes as Arduino: E01 unknown board, E02 unknown revision, E10 chip not answering, E11 release contradicted, E20 not on this board. E03 does not apply (no defines). E30/E31 belong to the screen project.
- Each (who, code) pair is reported once. The default logger is `print`, and `Steami.set_logger(fn)` replaces it (`set_logger(None)` silences it).

### Calibration

- Applied once per chip on first use, even when the release is forced, through the existing `steami_config` helpers: `apply_temperature_calibration`, `apply_magnetometer_calibration` and `apply_accelerometer_calibration`.
- The JSON keys (`tc`, `cm`, `ca`) are already the same as in Arduino.
- The chip at 0x5F on V1a and V1b is a WSEN-HIDS (wiki hardware pages). Its register map and WHO_AM_I (0xBC) match the HTS221, which is why the current samples and `steami_config/examples/calibrate_temperature.py` drive it with the HTS221 driver. That tool stores the real calibration under `tc.hts`, and an identity calibration (gain 1, offset 0) under `tc.hid`, the key Arduino reads. Builder's call, to keep existing calibrations: use `tc.hid` like Arduino, but use `tc.hts` when `tc.hid` is missing or is the identity.

### Changes outside `lib/steami`

- `daplink_bridge`: add `has_config_zone()`, a READ_SECTOR (0x20) probe of sector 0 with the same rules as Arduino. `Steami` calls it before any config read.
- Tests: a multi-address fake I2C bus with register images per chip (as Arduino's `steami_fake_chips.h`), and mock scenarios for detection (each origin, each release, prototype, E01/E02/E11), routing, absence values, calibration and messages. Hardware scenarios for at least one V1c.
- Firmware: add `require("steami", library="micropython-steami-lib")` to the STEAM32_WB55RG manifest in the fork, as a separate PR on `steamicc/micropython-steami`. Until it is merged, `lib/steami/.not-frozen` keeps `test_frozen_manifest` green.

## Left to the builder

- Which method of each existing driver to call for each read, and how to map each driver's units and errors to the absence values above.
- The exact split of `board.py` (it can be split further if it grows), and whether the routing table lives in its own module.
- The multi-address fake design, as long as existing tests keep working.
- Measuring the RAM cost (`gc.mem_free()` before and after `from steami import Temperature`, and with all classes) on the board, and reporting it in the pull request.
- The order of the work, and how many pull requests. Detection and `Steami`, then the classes in groups, is a natural order.
