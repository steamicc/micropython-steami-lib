# Testing

This project provides a test framework supporting both **mock tests** (no hardware required) and **hardware tests** (using a STeaMi board).

All tests are executed using `pytest`.

## Installation

```bash
make setup
```

This installs all dependencies (ruff, pytest, pyyaml via pip + git hooks via npm).

## Running tests

All test commands are available via `make`. Run `make help` to see the full list.

### Run mock tests

```bash
make test-mock
```

Executes tests using simulated registers. No hardware is required.

### Run all hardware tests

```bash
make test-hardware
```

Runs all tests on a connected STeaMi board (default port: `/dev/ttyACM0`).

### Run board-only tests (buttons, LEDs, buzzer, screen)

```bash
make test-board
```

### Run sensor driver hardware tests (I2C devices)

```bash
make test-sensors
```

### Run tests for a specific driver

```bash
make test-hts221
```

Per-scenario targets are generated automatically from `tests/scenarios/*.yaml`. Any YAML file added to that directory creates a corresponding `make test-<name>` target.

### Run all tests (mock + hardware)

```bash
make test-all
```

### Custom port

```bash
make test-hardware PORT=/dev/ttyACM1
```

### Board release

Some hardware tests only apply to one STeaMi release (see [Board release of a scenario](#board-release-of-a-scenario)). Before the first of them, the runner finds the release with `Steami.begin()` of `lib/steami`, run on the board with `lib/` mounted, and prints it (`[STeaMi] Board V1c (found by Steami.begin())`). The tests of the other releases are skipped with the reason, for example `needs a STeaMi V1a or V1b, this board is a V1c`.

When the board cannot tell its release, these tests are skipped. Give the release on the command line to skip the detection:

```bash
python -m pytest tests/ -v --port /dev/ttyACM0 -s -k hardware --release V1c
```

## Test reports

Test reports can be generated in Markdown format.

```bash
# Timestamped report
python -m pytest tests/ -v --port /dev/ttyACM0 --report auto

# Named report
python -m pytest tests/ -v --port /dev/ttyACM0 --report v1.0-validation
```

Reports are saved in the `reports/` directory and include:

* A global summary
* A detailed report per driver


## Adding tests for a new driver

Create a YAML scenario file in `tests/scenarios/<driver>.yaml`:

Each scenario describes:

* Initial register state
* Actions performed
* Expected results

Example structure:

```yaml
driver: hts221
driver_class: HTS221
i2c_address: 0x5F

i2c:
  id: 1

mock_registers:
  0x0F: 0xBC

tests:
  - name: "Verify device ID"
    action: read_register
    register: 0x0F
    expect: 0xBC
    mode: [mock, hardware]

  - name: "Temperature in plausible range"
    action: call
    method: temperature
    expect_range: [10.0, 45.0]
    mode: [hardware]
```

The test runner automatically discovers new YAML files.

### Board release of a scenario

A scenario whose chip is not on every release lists the releases it applies to with `releases`, using the names of `steami.Release` (`V1a`, `V1b`, `V1c`). The field may also be set on one test, and then replaces the value of the scenario:

```yaml
# tests/scenarios/apds9960.yaml: the APDS-9960 is not on the V1c
driver: apds9960
releases: [V1a, V1b]

# tests/scenarios/board_i2c_scan.yaml: one test per release
tests:
  - name: "BME280 chip ID (0x76)"
    releases: [V1c]
    ...
```

Only hardware tests are filtered; mock tests always run. Probing cannot tell a V1a from a V1b, so a board found as `V1a/V1b` runs the tests of `V1a` and of `V1b`. A scenario or test without `releases` runs on every board. `tests/test_scenario_release_mock.py` checks that every `releases` value is a known release.

### Naming convention

The Makefile generates a `make test-<name>` target for each YAML scenario. The target name comes from:

- **Driver scenarios**: the `driver` field in the YAML (e.g. `driver: wsen-hids` → `make test-wsen-hids`)
- **Board scenarios**: the filename stem (e.g. `board_buttons.yaml` → `make test-board_buttons`)

**Important**: for board scenarios (`type: board`), the `name` field in the YAML **must match the filename** (without `.yaml`). If they diverge, `make test-<name>` will not find any tests. For driver scenarios, the `driver` field is used and the filename can differ (e.g. `wsen_hids.yaml` with `driver: wsen-hids` works correctly).

### Requirements

* Provide at least **mock tests** for every driver
* Add **hardware tests** when possible
* Ensure all tests pass before submitting a Pull Request
