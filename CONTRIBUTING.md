# Contributing

This repository provides MicroPython drivers for the STeaMi board.
The goal is to maintain a consistent, reliable, and maintainable codebase across all drivers.

## Driver structure

Each driver must follow this layout:

```
lib/<component>/
├── README.md
├── manifest.py
├── <module_name>/
│   ├── __init__.py
│   ├── const.py
│   └── device.py
└── examples/
    └── *.py
```

### Requirements

* The directory name must match the driver name (e.g. `mcp23009e`, `wsen-hids`)
* The main class must be exposed in `__init__.py`
* Drivers must be self-contained (no cross-driver dependencies)

## Coding conventions

- **Constants**: use `from micropython import const` wrapper in `const.py` files.
- **Naming**: `snake_case` for all methods and variables. Enforced by ruff (N802, N803, N806).
- **Class inheritance**: `class Foo(object):` is the existing convention.
- **Time**: use `from time import sleep_ms` (not `utime`, not `sleep()` with float seconds).
- **Exceptions**: use `except Exception:` instead of bare `except:`.
- **No debug `print()`** in production driver code.

## Driver API conventions

- **Constructor signature**: `def __init__(self, i2c, ..., address=DEFAULT_ADDR)` — first parameter is always `i2c` (not `bus`), address uses keyword argument with a default from `const.py`.
- **Attributes**: `self.i2c` for the I2C bus, `self.address` for the device address (not `self.bus`, `self.addr`).
- **I2C helpers**: use private snake_case methods `_read_reg()`, `_write_reg()` for register access.
- **Device identification**: `device_id()` — returns the device/WHO_AM_I register value. All I2C drivers with an ID register must implement this method.
- **Reset methods**: `reset()` for hardware reset (pin toggle), `soft_reset()` for software reset (register write), `reboot()` for memory reboot (reload trimming).
- **Power methods**: `power_on()` / `power_off()`. All drivers must implement both.
- **Status methods**: `_status()` returns the raw status register as an int (private), `data_ready()` returns True when all channels have new data, `<measurement>_ready()` for per-channel readiness (e.g. `temperature_ready()`, `pressure_ready()`).
- **Measurement methods**: bare noun without unit suffix only for `temperature()` (°C) and `humidity()` (%RH). All others include the unit: `pressure_hpa()`, `distance_mm()`, `voltage_mv()`, `acceleration_g()`, etc. `read()` for combined reading returning a tuple, `<measurement>_raw()` for raw register values.
- **Mode methods**: `set_continuous(odr)` to start continuous measurements, `trigger_one_shot()` for a single conversion, `read_one_shot()` for trigger + wait + return data.

## Linting

The project uses `ruff` for linting.

```bash
ruff check .
```

To automatically fix issues:

```bash
ruff check . --fix
```

## Commit messages

Use the following format:

```
<scope>: <Description starting with a capital letter ending with a period.>
```

The scope is the driver name or domain (`hts221`, `ism330dl`, `docs`, `tests`, `ci`...). There is no predefined list of types — the scope is free-form.

### Examples

```
hts221: Fix missing self parameter in get_av method.
ism330dl: Add driver support for temperature reading.
wsen-pads: Correct pressure conversion formula.
docs: Update README driver table.
tests: Add mock scenarios for mcp23009e driver.
```

## Workflow

1. Create a branch from main (`git checkout -b my-new-feature`)
2. Write your code and add tests in `tests/scenarios/<driver>.yaml`
3. Run `ruff check` and `python -m pytest tests/ -v -k mock locally`
4. Commit your changes following the commit message format
5. Push your branch to the repository
6. Open a Pull Request

## Continuous Integration

All pull requests must pass these checks:

| Check | Workflow | Description |
|-------|----------|-------------|
| Commit messages | `check-commits.yml` | Validates commit message format |
| Linting | `python-linter.yml` | Runs `ruff check` |
| Mock tests | `tests.yml` | Runs mock driver tests |

## Notes

* Keep implementations simple and readable
* Follow existing drivers as reference
* Ensure documentation (`README.md`) and examples are included for each driver
