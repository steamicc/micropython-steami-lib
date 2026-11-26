# Board detection and function classes for MicroPython — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `steami` package that recognises the STeaMi release and offers thirteen function classes that pick the right chip, with the same behaviour as the Arduino library.

**Architecture:** `lib/steami/steami/` has `board.py` (the shared `Steami` object: detection, driver cache, calibration, messages), `handle.py` (the common base of the function classes), `const.py` (constants, routing and probe tables), and one module per function. `__init__.py` loads them lazily through a module-level `__getattr__`. `daplink_bridge` gains a `has_config_zone()` probe.

**Tech Stack:** MicroPython 1.29 (STM32WB55RG, firmware fork `steamicc/micropython-steami`, branch `stm32-steami-rev1d-final`). Mock tests on CPython with pytest (`make test-mock`, which runs `pytest tests/ -v -k mock`).

**Spec:** `docs/superpowers/specs/2026-11-26-steami-board-functions-design.md`

**Arduino reference:** `steamicc/arduino-steami-lib`, `lib/steami_board/src/` (read it with `git -C /home/nedjar/sandbox/arduino-steami-lib show origin/main:<path>`). When this plan says "as Arduino", copy the behaviour and the English texts from the file named.

## Global Constraints

- Public names are the Arduino ones in snake_case, without the `Steami` prefix on function classes (`Temperature`, not `SteamiTemperature`). The shared object keeps the name `Steami`.
- Release, chip and function constants are strings equal to the Arduino texts: `Release.V1A = "V1a"`, `Release.V1B = "V1b"`, `Release.V1C = "V1c"`, `Release.V1AB = "V1a/V1b"`, `Release.UNKNOWN = ""`; `Chip.BME280 = "BME280"`, `Chip.WSEN_HIDS = "WSEN-HIDS"`, `Chip.WSEN_PADS = "WSEN-PADS"`, `Chip.APDS9960 = "APDS-9960"`, `Chip.VL53L1X = "VL53L1X"`, `Chip.ISM330DL = "ISM330DL"`, `Chip.LIS2MDL = "LIS2MDL"`, `Chip.BQ27441 = "BQ27441"`, `Chip.MCP23009E = "MCP23009E"`.
- Messages: `[STeaMi] <who>: <detail> (Exx)`, each (who, code) printed once, through `print` by default. Codes and texts as Arduino `SteamiTypes.h`, `SteamiBoard.cpp` and `SteamiHandle.cpp`. No E03, E30 or E31.
- Absence values exactly as in the spec table (`float("nan")`, `-1`, `0`, `False`, `""`, `(0, 0, 0)`, `Gesture.NONE`).
- Creating any object touches no hardware. A failed function is not retried until `Steami.end()` or a reset.
- Drivers stay unchanged, except `daplink_bridge` (Task 1). No `print()` outside `steami/board.py`.
- Code must run on MicroPython 1.29 and on CPython for the mock tests: no CPython-only modules. `collections.namedtuple` is fine.
- Constants of integer type go in `const.py` with `const()`, as in the other drivers (CONTRIBUTING.md).
- Commits: Conventional Commits with a scope from `commitlint.config.js`, the subject ending with a period, the header at most 78 characters. Task 1 adds the `steami` scope.
- Internal bus: `machine.I2C(1)`. Buttons: `Pin("A_BUTTON")`, `Pin("B_BUTTON")`, `Pin("MENU_BUTTON")`, with a pull-up, active low. MCP23009E: address 0x20, reset pin `Pin("RST_EXPANDER", Pin.OUT)`.

## Review Focus

- **No DAPLink bridge on the bus**, or an I2C error at 0x3B (an old board, or a bus fault): detection must fall through to probing without an exception. Tested in Task 3.
- **A config zone that holds empty or invalid JSON**: it counts as "no revision", without a crash, then probing. Tested in Task 3.
- **A driver constructor that raises something other than `OSError`** (for example `WSENPADSDeviceNotFound`, or `ValueError` on a wrong WHO_AM_I): `claim()` must return `Status.NOT_RESPONDING`. Tested in Task 4.
- **`Steami.begin()` called a second time with another forced release**: it is ignored. Detection runs once, as in Arduino. Tested in Task 3.
- **Reads repeated after a failed `begin()`**: they return the absence value with no new I2C traffic and no new message. Tested in Task 5.

---

### Task 1: `daplink_bridge.has_config_zone()` and the `steami` commit scope

**Files:**
- Modify: `lib/daplink_bridge/daplink_bridge/const.py` (add `CMD_READ_SECTOR = const(0x20)`, `PROBE_TIMEOUT_MS = const(500)`, `PROBE_SETTLE_MS = const(150)`)
- Modify: `lib/daplink_bridge/daplink_bridge/device.py` (add `has_config_zone()`)
- Modify: `commitlint.config.js` (add `'steami'` to `scope-enum`)
- Test: `tests/scenarios/daplink_bridge.yaml` (new mock tests)

**Interfaces:**
- Produces: `DaplinkBridge.has_config_zone() -> bool`. It probes once, and the result is cached in `self._config_zone` (`None` = not probed yet, `True`, `False`). An unknown result is not cached and returns `False`.

- [ ] **Step 1: Write the failing mock tests** in `daplink_bridge.yaml`, as `action: script` with `mode: [mock]`. Each one sets the error register (0x81) and the status register (0x80) of the fake, then checks `dev.has_config_zone()`:
  - "Config zone present": error 0x00, status 0x00 → `True`, and the write log contains `(0x20, b"\x00\x00")`.
  - "Config zone absent (old firmware)": error read 0x00 before the probe and 0x80 after it (`set_register_sequence(0x81, [b"\x00", b"\x80"])`) → `False`.
  - "Bridge still busy": status 0x80 at every read → `False`, and a second call probes again (the write log has two READ_SECTOR frames).
  - "Result cached": after a `True`, a second call adds no write.
- [ ] **Step 2: Run them, expect failures.** `python -m pytest tests/ -v -k "mock and daplink_bridge"` → the new tests FAIL with `AttributeError: has_config_zone`.
- [ ] **Step 3: Implement `has_config_zone()`** as Arduino `SteamiDaplinkBridge::hasConfigZone()`/`probeConfigZone()`/`commandResult()` (`lib/daplink_bridge/src/SteamiDaplinkBridge.cpp:43-77` and `304-325`). Wait until not busy (500 ms), read the error register to clear it, write the frame `CMD_READ_SECTOR, 0x00, 0x00`, sleep 150 ms, read error then status. Busy → unknown (wait until not busy, return `False`, no caching). Error 0 → `True`. Otherwise → `False`. Any `OSError` → unknown.
- [ ] **Step 4: Run the tests.** Same command → all PASS, and the existing bridge tests still PASS.
- [ ] **Step 5: Commit.** `git commit -m "feat(daplink_bridge): Probe the config zone before using it."` (the commitlint change goes in the same commit).

### Task 2: Multi-device fake bus and chip images

**Files:**
- Create: `tests/fake_machine/i2c_bus.py`
- Create: `tests/fake_machine/steami_chips.py`
- Test: `tests/test_fake_bus_mock.py`

**Interfaces:**
- Produces: `FakeI2CBus(devices: dict[int, dict[int, bytes|int]])`, with the same methods as `FakeI2C` (`readfrom_mem`, `readfrom_mem_into`, `writeto_mem`, `readfrom`, `writeto`, `writevto`, `scan`, `set_register_sequence(addr, reg, values)`, `get_write_log()` returning `(addr, reg, data)`). An address that is not in `devices` raises `OSError(19)` (ENODEV), as the board does.
- Produces: `steami_chips.image(chip: str) -> dict` (register image for one chip, keyed like `Chip.*` texts), `steami_chips.ADDRESS: dict[str, int]`, and `steami_chips.board(release: str, missing=()) -> FakeI2CBus` (the chips of `"V1a/V1b"` or `"V1c"` plus the DAPLink bridge at 0x3B, minus the `missing` ones).

- [ ] **Step 1: Write the failing test** `tests/test_fake_bus_mock.py`: for each chip of each release, load its driver with `load_driver_mock` and construct it on `steami_chips.board(release)`, with no exception. Also: a read at an absent address raises `OSError`.
- [ ] **Step 2: Run it, expect failure.** `python -m pytest tests/test_fake_bus_mock.py -v` → FAIL with `ModuleNotFoundError: tests.fake_machine.i2c_bus`.
- [ ] **Step 3: Implement the bus and the images.** The images hold what each driver constructor reads: WHO_AM_I and calibration registers (BME280 0xD0 = 0x60, WSEN-HIDS 0x0F = 0xBC, WSEN-PADS 0x0F = 0xB3, APDS-9960 0x92 = 0xAB…). The values come from the existing YAML scenarios of each driver, and the Arduino `tests/shared/steami_fake_chips.h` can help.
- [ ] **Step 4: Run it.** Same command → PASS. `make test-mock` → no regression.
- [ ] **Step 5: Commit.** `git commit -m "test(tests): Add a multi-device fake I2C bus with STeaMi chip images."`

### Task 3: `Steami` release detection and messages

**Files:**
- Create: `lib/steami/manifest.py` (`package("steami")`), `lib/steami/.not-frozen` (`Pending firmware manifest.`), `lib/steami/steami/const.py`, `lib/steami/steami/board.py`
- Test: `tests/test_steami_board_mock.py`

**Interfaces:**
- Consumes: `DaplinkBridge.has_config_zone()` (Task 1), `SteamiConfig(bridge).load()` and `.board_revision`, `steami_chips.board()` (Task 2).
- Produces, in `const.py`: `Release`, `Chip`, `Function`, `Status` (`OK`, `NOT_STARTED`, `NOT_RESPONDING`, `NOT_ON_THIS_BOARD`, `UNKNOWN_BOARD`), `Origin` (`NONE`, `FORCED`, `CONFIG`, `PROBE`), the probe table `PROBES` (as Arduino `kProbes`, `SteamiBoard.cpp:44-49`), and `decode_revision(rev) -> (release, is_prototype) | None` (as `steamiDecodeRevision`, `SteamiTypes.h`).
- Produces, in `board.py`: a module-level instance `Steami` of class `_Board`, with `begin(release=None) -> str`, `release() -> str`, `release_name() -> str`, `origin() -> str`, `revision() -> int|None`, `is_prototype() -> bool`, `is_v1c() -> bool`, `is_v1ab() -> bool`, `i2c()`, `config() -> SteamiConfig|None`, `report(who: str, code: str, detail: str)`, `set_logger(fn|None)`, `last_error() -> str`, `end()` (forget everything: release, drivers, messages already sent; used by tests).

- [ ] **Step 1: Write the failing tests.** Each one builds a board with `steami_chips.board(...)`, injects it with `Steami._i2c = bus` after `Steami.end()`, captures messages with `Steami.set_logger(lines.append)`, then checks:
  - `test_mock_forced`: `Steami.begin("V1c")` → `release() == "V1c"`, `origin() == Origin.FORCED`, no I2C read in the write or read logs.
  - `test_mock_config_rev_131`: bridge config `{"rev": 131}` → `"V1c"`, `Origin.CONFIG`, `revision() == 131`, `is_prototype() is False`, and the banner line `[STeaMi] Board V1c (read from the board config, revision 131)`.
  - `test_mock_config_rev_130_prototype`: `is_prototype() is True`, and the banner ends with `, prototype)`.
  - `test_mock_config_rev_111` and `_121`: `"V1a"`, `"V1b"`.
  - `test_mock_config_invalid_rev`: `{"rev": 42}` → message E02, then probing gives `"V1c"` with `Origin.PROBE`.
  - `test_mock_config_bad_json` and `test_mock_config_empty`: no exception, probing.
  - `test_mock_no_config_zone`: `has_config_zone()` is `False` → no config command written, probing.
  - `test_mock_no_bridge`: no device at 0x3B → probing, no exception.
  - `test_mock_probe_v1c`: `"V1c"` and the banner `(detected: BME280 at 0x76)`.
  - `test_mock_probe_v1ab`: `"V1a/V1b"`, `is_v1ab() is True`.
  - `test_mock_unknown`: no chip → `Release.UNKNOWN`, the banner `(nothing detected)` and E01, once even after a second `begin()`.
  - `test_mock_begin_once`: `begin()`, then `begin("V1a")` → the release is unchanged.
  - `test_mock_logger_none`: `set_logger(None)` → nothing printed, and `last_error()` still holds the last code.
- [ ] **Step 2: Run them, expect failures.** `python -m pytest tests/test_steami_board_mock.py -v` → FAIL (`steami` not found). The test loads `lib/steami` and its dependencies the way `tests/runner/executor.py` does, with the fake `machine`, `micropython` and `time` modules, and adds `lib/daplink_bridge` and `lib/steami_config` to `sys.path`.
- [ ] **Step 3: Implement `const.py` and `board.py`.** Detection follows `SteamiBoard.cpp` `detect()` (312-328), `loadConfig()` (330-346), `detectFromConfig()` (348-371), and `report()` (203-231) for the once-only rule. Banner texts as Arduino, except the `#define` origin, which does not exist here. `i2c()` creates `machine.I2C(1)` on first call.
- [ ] **Step 4: Run them.** Same command → PASS. `make test-mock` → no regression.
- [ ] **Step 5: Commit.** `git commit -m "feat(steami): Recognise the board release."`

### Task 4: Shared drivers and calibration

**Files:**
- Modify: `lib/steami/steami/board.py`, `lib/steami/steami/const.py` (add the driver factory table: chip → module, class, address)
- Test: `tests/test_steami_board_mock.py`

**Interfaces:**
- Produces: `Steami.claim(chip) -> str` (`Status.OK` or `Status.NOT_RESPONDING`, cached per chip), the accessors `bme280()`, `wsen_hids()`, `wsen_pads()`, `apds9960()`, `vl53l1x()`, `ism330dl()`, `lis2mdl()`, `bq27441()`, `mcp23009e()` (the shared driver or `None`), `calibrate(chip) -> bool`, `calibrated(chip) -> bool`, `has(function) -> bool`, and `print_info()`.

- [ ] **Step 1: Write the failing tests:**
  - `test_mock_claim_shared`: two `claim(Chip.ISM330DL)` calls create one driver (same object from `ism330dl()`).
  - `test_mock_claim_missing`: chip absent → `Status.NOT_RESPONDING`, accessor `None`.
  - `test_mock_claim_custom_exception`: a fake whose WSEN-PADS WHO_AM_I is wrong, so the driver raises its own exception → `Status.NOT_RESPONDING`, no exception out of `claim()`.
  - `test_mock_calibrate_bme280`: config `{"tc": {"bme": {"gain": 1.1, "offset": -0.5}}}` → `calibrated(Chip.BME280) is True` and the driver's `_temp_gain`/`_temp_offset` are set. A second `calibrate()` does nothing.
  - `test_mock_calibrate_hids_falls_back_to_hts`: `{"tc": {"hid": {"gain": 1.0, "offset": 0.0}, "hts": {"gain": 1.05, "offset": 0.3}}}` → the HTS values are applied. With a non-identity `hid`, `hid` wins.
  - `test_mock_calibrate_forced_release`: the calibration is applied even after `begin("V1c")`.
  - `test_mock_has`: on V1c, `has(Function.LIGHT) is False` and `has(Function.TEMPERATURE) is True`.
  - `test_mock_print_info`: on V1c, before any claim, one line per chip of the release with `not tried`. After `claim(Chip.BME280)` with a calibration, `BME280 0x76 OK, calibrated`. The format is as Arduino `printInfo()`.
- [ ] **Step 2: Run them, expect failures.** `python -m pytest tests/test_steami_board_mock.py -v -k "claim or calibrate or has or print_info"` → FAIL.
- [ ] **Step 3: Implement.** `claim()` imports the driver module only when it is first needed, and catches `Exception` around the constructor. Calibration uses `SteamiConfig.apply_temperature_calibration`, `apply_magnetometer_calibration` and `apply_accelerometer_calibration`. The `hid`/`hts` rule is the one of the spec: `hts` when `hid` is missing, or is exactly gain 1.0 and offset 0.0. The MCP23009E needs `Pin("RST_EXPANDER", Pin.OUT)`.
- [ ] **Step 4: Run them.** Same command → PASS.
- [ ] **Step 5: Commit.** `git commit -m "feat(steami): Share chip drivers and apply calibrations."`

### Task 5: Common handle and the environment classes

**Files:**
- Create: `lib/steami/steami/handle.py`, `temperature.py`, `humidity.py`, `pressure.py`
- Modify: `lib/steami/steami/const.py` (add `ROUTES`, the routing table of the spec)
- Test: `tests/test_steami_functions_mock.py`

**Interfaces:**
- Produces: `class Handle` with `__init__(self, function)`, `begin() -> bool`, `is_available() -> bool`, `status() -> str`, `error() -> str`, `chip() -> str`, and the protected `_driver()` returning the claimed driver or `None` after an implicit `begin()`. `Temperature.read() -> float`, `Temperature.set_offset(offset_c)`, `Humidity.read() -> float`, `Pressure.read() -> float`, `Pressure.altitude(sea_level_hpa=1013.25) -> float`.

- [ ] **Step 1: Write the failing tests:**
  - Routing: on V1c, `Temperature().chip() == "BME280"`. On V1a/V1b, `"WSEN-HIDS"`. On V1a/V1b without WSEN-HIDS, `"WSEN-PADS"`. With an unknown release, the candidates are tried in the order BME280, WSEN-HIDS, WSEN-PADS. `Humidity` and `Pressure` are checked the same way against the spec table.
  - Reads: `read()` returns the value the driver computes from the fake registers, and `Pressure.altitude()` matches the driver's `altitude()`.
  - Absence: the chip is missing → `begin() is False`, `status() == Status.NOT_RESPONDING`, `error() == "no answer"`, `read()` returns `nan` (`math.isnan`), and the message is E10.
  - E11: as Arduino `SteamiHandle.cpp:83-131`. Write one test per case that code distinguishes.
  - Review Focus: after a failed `begin()`, ten `read()` calls add nothing to the bus read log, and no new message appears.
  - `Temperature()` without `begin()`: no bus access until the first `read()`.
- [ ] **Step 2: Run them, expect failures.** `python -m pytest tests/test_steami_functions_mock.py -v` → FAIL.
- [ ] **Step 3: Implement `Handle` and the three classes.** `Handle.begin()` follows `SteamiHandle::begin()` (`SteamiHandle.cpp` around 29-58): `Steami.begin()`, the candidates from `ROUTES`, then the first chip whose `claim()` succeeds, then `calibrate()`. The status, error texts and messages come from `SteamiHandle.cpp:83-131`. `set_offset()` adds to the calibrated reading, as Arduino.
- [ ] **Step 4: Run them.** Same command → PASS.
- [ ] **Step 5: Commit.** `git commit -m "feat(steami): Add Temperature, Humidity and Pressure."`

### Task 6: Distance and Battery

**Files:**
- Create: `lib/steami/steami/distance.py`, `battery.py`
- Test: `tests/test_steami_functions_mock.py`

**Interfaces:**
- Consumes: `Handle` (Task 5).
- Produces: `Distance.read() -> int` (mm) and `Distance.cm() -> float`. `Battery.percent() -> int`, `Battery.voltage() -> float` (V), `Battery.current() -> int` (mA) and `Battery.is_charging() -> bool`.

- [ ] **Step 1: Write the failing tests.** Values come from the fake registers. With the chip missing: `-1` and `nan` for distance, and `0`, `nan`, `0`, `False` for the battery. `is_charging()` follows the sign rule of Arduino `SteamiBattery.cpp`.
- [ ] **Step 2: Run them, expect failures.** `python -m pytest tests/test_steami_functions_mock.py -v -k "distance or battery"` → FAIL.
- [ ] **Step 3: Implement both classes.** `Distance` starts ranging in `begin()`, as Arduino `SteamiDistance.cpp`.
- [ ] **Step 4: Run them.** Same command → PASS.
- [ ] **Step 5: Commit.** `git commit -m "feat(steami): Add Distance and Battery."`

### Task 7: Motion, magnetometer and compass

**Files:**
- Create: `lib/steami/steami/accelerometer.py`, `gyroscope.py`, `magnetometer.py`, `compass.py`
- Modify: `lib/steami/steami/const.py` (add `Vector = namedtuple("Vector", ("x", "y", "z"))`)
- Test: `tests/test_steami_functions_mock.py`

**Interfaces:**
- Produces: `Accelerometer.read() -> Vector` (g), `.x()`, `.y()`, `.z()`, `.strength()`, `.is_shaken(threshold_g=2) -> bool`. `Gyroscope.read() -> Vector` (dps), `.x()`, `.y()`, `.z()`. `Magnetometer.read() -> Vector` (µT), `.x()`, `.y()`, `.z()`, `.strength()`, `.calibrate(seconds=12)`. `Compass.heading() -> float`, `.direction() -> str`, `.set_declination(deg)`, `.calibrate(seconds=12)`.

- [ ] **Step 1: Write the failing tests.**
  - Accelerometer and Gyroscope share one ISM330DL (same object from `Steami.ism330dl()`).
  - `Accelerometer.begin()` writes ±8 g at 104 Hz (the CTRL1_XL value in the write log).
  - Vectors from the fake registers. Absence gives `Vector(nan, nan, nan)` and `is_shaken() is False`.
  - Heading of a known field. The `direction()` texts and sectors as Arduino `SteamiCompass.cpp`, which gives `""` when absent.
- [ ] **Step 2: Run them, expect failures.** `python -m pytest tests/test_steami_functions_mock.py -v -k "accel or gyro or magnet or compass"` → FAIL.
- [ ] **Step 3: Implement the four classes.** `calibrate()` stores the result in the driver, not in the config zone, as Arduino.
- [ ] **Step 4: Run them.** Same command → PASS.
- [ ] **Step 5: Commit.** `git commit -m "feat(steami): Add motion, magnetometer and compass classes."`

### Task 8: Light, Color and Gesture

**Files:**
- Create: `lib/steami/steami/light.py`, `color.py`, `gesture.py`
- Test: `tests/test_steami_functions_mock.py`

**Interfaces:**
- Produces: `Light.read() -> int`. `Color.read() -> tuple` `(r, g, b)`, `.red()`, `.green()`, `.blue()`. `Gesture.read(timeout_ms=...) -> str`, with the constants `Gesture.NONE`, `UP`, `DOWN`, `LEFT`, `RIGHT`, and `.name()`. Constants, names and the default timeout as Arduino `SteamiGesture.h`.

- [ ] **Step 1: Write the failing tests.** Values on V1a/V1b. On V1c: `begin() is False`, `status() == Status.NOT_ON_THIS_BOARD`, `error() == "not on this board"`, message E20, and the absence values `0`, `(0, 0, 0)` and `Gesture.NONE`. The three classes share one APDS-9960.
- [ ] **Step 2: Run them, expect failures.** `python -m pytest tests/test_steami_functions_mock.py -v -k "light or color or gesture"` → FAIL.
- [ ] **Step 3: Implement the three classes.**
- [ ] **Step 4: Run them.** Same command → PASS.
- [ ] **Step 5: Commit.** `git commit -m "feat(steami): Add Light, Color and Gesture."`

### Task 9: Buttons

**Files:**
- Create: `lib/steami/steami/buttons.py`
- Test: `tests/test_steami_functions_mock.py`

**Interfaces:**
- Produces: `Buttons.is_pressed(name) -> bool`, `.was_pressed(name) -> bool`, `.was_released(name) -> bool`, `.wait_for_press(timeout_ms=None) -> str|None`. Names: `"A"`, `"B"`, `"MENU"`, `"UP"`, `"DOWN"`, `"LEFT"`, `"RIGHT"`. Debounce of 20 ms. D-pad bits on the MCP23009E as Arduino `SteamiButtons.cpp`.

- [ ] **Step 1: Write the failing tests** with `FakePin` and the fake MCP23009E:
  - a press shorter than 20 ms is ignored, a longer one gives one `was_pressed`;
  - an unknown name raises `ValueError`;
  - without an MCP23009E, the D-pad stays released while A, B and MENU still work.
- [ ] **Step 2: Run them, expect failures.** `python -m pytest tests/test_steami_functions_mock.py -v -k buttons` → FAIL.
- [ ] **Step 3: Implement `Buttons`.** Polling, as Arduino: no interrupts.
- [ ] **Step 4: Run them.** Same command → PASS.
- [ ] **Step 5: Commit.** `git commit -m "feat(steami): Add Buttons."`

### Task 10: Lazy package, README and examples

**Files:**
- Create: `lib/steami/steami/__init__.py`, `lib/steami/README.md`, `lib/steami/examples/board_info.py`, and one example per class (`temperature.py` … `buttons.py`, the same programs as Arduino `examples/STEAMI_BOARD/*`)
- Test: `tests/test_steami_board_mock.py`, `tests/test_examples.py` (existing)

**Interfaces:**
- Produces: `from steami import X` for `Steami`, `Release`, `Chip`, `Function`, `Status`, `Vector` and the thirteen classes.

- [ ] **Step 1: Write the failing test** `test_mock_lazy_import`: after `import steami`, none of `steami.temperature` … `steami.buttons` is in `sys.modules`. After `from steami import Temperature`, only `steami.temperature`, `steami.handle`, `steami.board` and `steami.const` are.
- [ ] **Step 2: Run it, expect failure.** `python -m pytest tests/test_steami_board_mock.py -v -k lazy` → FAIL.
- [ ] **Step 3: Implement `__init__.py`.** It holds a dict from public name to submodule, and a module-level `__getattr__` that imports the submodule and caches the attribute in the module globals. Write the README (what it does, the routing table, the absence values, the messages) and the examples.
- [ ] **Step 4: Run all mock tests and the example check.** `make test-mock && make test-examples` → PASS. `ruff check lib/steami` → clean.
- [ ] **Step 5: Commit.** `git commit -m "feat(steami): Load function classes lazily, add README and examples."`

### Task 11: Validation on the V1c

**Files:**
- Create: `tests/scenarios/steami_board.yaml` (hardware mode only)

- [ ] **Step 1: Write the hardware scenario.**
  - `Steami.begin()` returns `"V1c"`.
  - `Temperature().chip() == "BME280"`, and `read()` is between 0 and 50 °C.
  - `Light().status() == Status.NOT_ON_THIS_BOARD`.
  - `Battery().voltage()` is between 3.0 and 4.4 V.
  - `Buttons().is_pressed("A") is False`.
- [ ] **Step 2: Ask for the board.** It is shared: ask the other sessions for a slot. Flash the release firmware, then copy `lib/steami` and its dependencies with `mpremote`.
- [ ] **Step 3: Run it.** `python -m pytest tests/ -v -k steami_board --port /dev/ttyACM0` → PASS.
- [ ] **Step 4: Measure the RAM.** Read `gc.collect(); gc.mem_free()` in four cases: before any import, after `from steami import Temperature` and a `read()`, after importing all thirteen classes, and with a BLE sample of micropython-steami-sample (`ble/beacon`) changed locally to read through `Temperature()` instead of the WSEN-PADS. That sample must advertise and be seen from the PC (`bluetoothctl`). Write the four numbers in the pull request.
- [ ] **Step 5: Put battery_status back, release the board, commit.** `git commit -m "test(steami): Add the V1c hardware scenario."`

### Task 12: Freeze `steami` in the firmware

**Files:**
- Modify (fork `steamicc/micropython-steami`, branch `stm32-steami-rev1d-final`): `ports/stm32/boards/STEAM32_WB55RG/manifest.py`, adding `require("steami", library="micropython-steami-lib")`
- Modify (this repo, after the fork PR is merged): delete `lib/steami/.not-frozen`

- [ ] **Step 1: Open the fork PR** once the library PR is merged. The firmware must build with `make micropython-firmware`, and `import steami` must work on the board.
- [ ] **Step 2: After the fork PR is merged,** delete `.not-frozen` and run `python -m pytest tests/test_frozen_manifest.py -v` → PASS.
- [ ] **Step 3: Commit.** `git commit -m "fix(steami): Freeze the package in the firmware."` A `fix` commit triggers a release, so the release firmware includes `steami`.
