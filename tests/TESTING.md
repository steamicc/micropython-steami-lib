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

### Requirements

* Provide at least **mock tests** for every driver
* Add **hardware tests** when possible
* Ensure all tests pass before submitting a Pull Request
