# Testing

This project provides a test framework supporting both **mock tests** (no hardware required) and **hardware tests** (using a STeaMi board).

All tests are executed using `pytest`.

## Installation

Install the required dependencies:

```bash
pip install pytest pyyaml
```

## Running tests

### Run mock tests

```bash
python -m pytest tests/ -v -k mock
```

Executes tests using simulated registers. No hardware is required.

### Run hardware tests

```bash
python -m pytest tests/ -v --port /dev/ttyACM0
```

Runs tests on a connected STeaMi board.

### Run tests for a specific driver

```bash
python -m pytest tests/ -v --driver hts221 --port /dev/ttyACM0
```

Limits execution to a single driver.

### Run interactive tests

```bash
python -m pytest tests/ -v --port /dev/ttyACM0 -s
```

Displays live output and allows manual verification.

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
