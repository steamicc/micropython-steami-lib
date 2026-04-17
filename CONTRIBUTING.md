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
* Every driver is automatically checked against the upstream firmware manifest by `tests/test_frozen_manifest.py`. If a driver is intentionally **not** frozen (experimental, not yet integrated, etc.), add a `lib/<driver>/.not-frozen` marker file (it may be empty; optionally include a one-line reason) — the test will skip it and display the reason if present.

## Coding conventions

- **Constants**: use `from micropython import const` wrapper in `const.py` files.
- **Imports**: explicit imports only (`from <module>.const import NAME1, NAME2`). Wildcard `import *` is not allowed.
- **Naming**: `snake_case` for all methods and variables. Enforced by ruff (N802, N803, N806).
- **Class inheritance**: `class Foo(object):` is the existing convention.
- **Time**: use `from time import sleep_ms` (not `utime`, not `sleep()` with float seconds).
- **Exceptions**: use `except Exception:` instead of bare `except:`. Enforced by ruff (E722).
- **No debug `print()`** in production driver code. Enforced by ruff (T20, examples and tests excluded).
- **`@micropython.native`**: do **not** use in driver code (`device.py`) — methods are dominated by I2C/SPI bus time, so native compilation gains nothing and reduces debuggability. In **examples**, it may be used on rendering hot-paths (tight pixel loops, math-heavy drawing functions) where a measurable speedup is expected. Do not apply it to functions with only a few comparisons or I/O calls. Note: the native emitter does not support generators, closures, or `with` statements.

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

```bash
make lint
```

To automatically fix issues:

```bash
make lint-fix
```

### Active ruff rules

The full configuration is in `pyproject.toml` (`[tool.ruff.lint]` section). The table below highlights the most impactful rule groups; additional groups (ASYNC, DTZ, EXE, G, ICN, INT, ISC, PGH, PIE, PYI, RSE, T10, TCH, YTT) are also enabled — refer to `pyproject.toml` for the complete list.

| Group | Description |
|-------|-------------|
| A | Prevent shadowing Python builtins |
| B | Flake8-bugbear: common bug patterns |
| C4 / C90 | Comprehension style / McCabe cyclomatic complexity |
| E / W | Pycodestyle errors and warnings |
| F | Pyflakes (unused imports, undefined names, etc.) |
| I | Import sorting (isort) |
| N802, N803, N806 | PEP 8 naming: functions, arguments, and variables must be `snake_case` |
| PL | Pylint (complexity thresholds: max-branches=25, max-statements=65, max-args=10) |
| PERF | Perflint: performance anti-patterns |
| S110 | Flake8-bandit: no silent `try/except: pass` |
| SIM | Flake8-simplify: code simplification suggestions |
| T20 | No `print()` in production code (excluded for examples and tests) |
| RUF | Ruff-specific rules |

### Explicit preview rules

Some pycodestyle rules are in ruff's preview tier and must be enabled individually (because `explicit-preview-rules = true`). These catch formatting issues that were previously missed in PRs:

| Rule | Description |
|------|-------------|
| E203 | Whitespace before `:`, `;`, or `,` (catches `else :`) |
| E225 | Missing whitespace around operator |
| E231 | Missing whitespace after `,` |
| E261 | At least two spaces before inline comment |
| E262 | Inline comment must start with `# ` |
| E265 | Block comment must start with `# ` |
| E275 | Missing whitespace after keyword (catches `if(...)`) |
| E301 | Blank line between methods |
| E302 | Expected 2 blank lines before function/class definition |
| E303 | Too many blank lines |
| E305 | Expected 2 blank lines after function/class definition |
| W391 | Too many newlines at end of file |

### MicroPython-specific exceptions

Some rules are ignored because MicroPython does not support the corresponding Python features:

| Ignored rule | Reason |
|--------------|--------|
| B905 | `zip(strict=)` is not available in MicroPython |
| ISC003 | MicroPython does not support implicit concatenation of f-strings |
| PIE810 | MicroPython does not support passing tuples to `.startswith()` / `.endswith()` |
| SIM101 | `isinstance()` with merged tuple arguments is unreliable in MicroPython |
| SIM105 | `contextlib.suppress` is not available in MicroPython |

## Commit messages

Commit messages follow the [Conventional Commits](https://www.conventionalcommits.org/) format, enforced by commitlint via a git hook:

```
<type>[(<scope>)]: <Description starting with a capital letter ending with a period.>
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `ci`, `build`, `chore`, `perf`, `revert`, `tooling`

**Scopes** (optional but enforced): if provided, the scope **must** be one of the allowed values. The scope is recommended for driver-specific changes but can be omitted for cross-cutting changes.

- Driver scopes: `apds9960`, `bme280`, `bq27441`, `daplink_bridge`, `daplink_flash`, `gc9a01`, `hts221`, `im34dt05`, `ism330dl`, `lis2mdl`, `mcp23009e`, `ssd1327`, `steami_config`, `vl53l1x`, `wsen-hids`, `wsen-pads`, `steami_screen` 
- Domain scopes: `ci`, `docs`, `style`, `tests`, `tooling`

### Examples

```
fix(hts221): Fix missing self parameter in get_av method.
feat(ism330dl): Add driver support for temperature reading.
fix(wsen-pads): Correct pressure conversion formula.
docs: Update README driver table.
test(mcp23009e): Add mock scenarios for mcp23009e driver.
```

## Prerequisites

For local development (without dev container):

* Python 3.10+
* Node.js 22+ (for husky, commitlint, lint-staged, semantic-release)
* `arm-none-eabi-gcc` toolchain (for `make micropython-firmware`; `make daplink-firmware` ignores the system toolchain and downloads its own pinned 10.3-2021.10 build)
* `ccache` and `ninja-build` (for `make daplink-firmware`)
* For `make daplink-firmware`: Linux x86_64, Linux aarch64, or Intel macOS only (the pinned toolchain is not published for Apple Silicon or Windows — use the dev container on those platforms)
* `pyocd` (for `make micropython-deploy`, installed via `pip install -e ".[flash]"`)
* OpenOCD (optional, for `make micropython-deploy-openocd`)
* `mpremote` (installed via `pip install -e ".[test]"`)
* GitHub CLI (`gh`)

Then run `make setup` to install all dependencies and git hooks. This creates a `.venv` with ruff, pytest, mpremote, and MicroPython type stubs for Pylance.

## Dev Container

A dev container is available for VS Code (local Docker only, not GitHub Codespaces). It includes all prerequisites out of the box: Python 3.10, Node.js 22, ruff, pytest, mpremote, pyOCD, arm-none-eabi-gcc, OpenOCD, ccache, ninja-build, and the GitHub CLI.

1. Open the repository in VS Code
2. When prompted, click **Reopen in Container** (or use the command palette: *Dev Containers: Reopen in Container*)
3. The container runs `make setup` automatically on creation

The container also provides:

* **zsh + oh-my-zsh** as default shell with persistent shell history
* **Pylance** configured with MicroPython STM32 stubs via `[tool.pyright]` in `pyproject.toml` (no false `import machine` errors)
* **Serial Monitor** extension for board communication
* **USB passthrough** for mpremote, pyOCD, OpenOCD, and MicroPython firmware flashing (the container runs in privileged mode with `/dev/bus/usb` mounted)
* **udev rules** for the DAPLink interface (auto-started on container creation)

Note: GitHub Codespaces is not supported because the container requires privileged mode and USB device access for board communication.

## Workflow

1. Set up your environment: open in the dev container, or run `make setup` locally
2. Create a branch from main (format: `feat/`, `fix/`, `docs/`, `tooling/`, `ci/`, `test/`, `style/`, `chore/`, `refactor/`)
3. Write your code and add tests in `tests/scenarios/<driver>.yaml`
4. Run `make ci` to verify everything passes (lint + tests + examples)
5. Commit — the git hooks will automatically check your commit message and run ruff on staged files
6. Push your branch and open a Pull Request

If git hooks fail because `node_modules/` is missing (for example on a fresh clone or after `make deepclean`), run `make setup` or `npm install` before committing.

### Line endings

The repository enforces **LF line endings** on all text files via `.gitattributes`. This prevents CRLF shebangs from breaking husky hooks on Windows + WSL. If you have an existing clone on Windows, run `git add --renormalize .` after pulling the `.gitattributes` change to re-normalize your working tree.

## Continuous Integration

All pull requests must pass these checks:

| Check | Workflow | Description |
|-------|----------|-------------|
| Commit messages | `check-commits.yml` | Validates commit message format |
| Linting | `python-linter.yml` | Runs `ruff check` |
| Mock tests | `tests.yml` | Runs mock driver tests |
| Example validation | `tests.yml` | Validates example files syntax and imports |
| Frozen manifest | `tests.yml` | Verifies every `lib/*/` driver is declared in the upstream firmware manifest |

## Releasing

Releases are handled automatically by [semantic-release](https://semantic-release.gitbook.io/) when commits are pushed to `main`. The version is determined from commit messages:

- `fix:` → patch bump (v1.0.0 → v1.0.1)
- `feat:` → minor bump (v1.0.0 → v1.1.0)
- `BREAKING CHANGE:` in commit body → major bump (v1.0.0 → v2.0.0)
- `docs:`, `style:`, `test:`, `ci:`, `chore:` → no release

semantic-release automatically updates `pyproject.toml`, generates `CHANGELOG.md`, creates a git tag, and publishes a GitHub release with both firmwares attached:

- **MicroPython firmware**: `steami-micropython-firmware-vX.Y.Z.hex` / `.bin`
- **DAPLink interface firmware**: `steami-daplink-firmware-vX.Y.Z.hex` / `.bin`

To force a specific version manually (override):

```bash
make bump              # patch: v1.0.0 → v1.0.1
make bump PART=minor   # minor: v1.0.1 → v1.1.0
make bump PART=major   # major: v1.1.0 → v2.0.0
```

## MicroPython firmware build and deploy

The STeaMi board has two distinct firmwares:

- **MicroPython firmware** — runs on the STM32WB55 main MCU and exposes the drivers from this repository
- **DAPLink firmware** — runs on the STM32F103 interface chip and provides the I2C bridge, mass-storage, and CMSIS-DAP debug interface

The drivers in this repository are "frozen" into the **MicroPython firmware**. The Makefile automates cloning, building, and flashing both firmwares.

### MicroPython firmware

```bash
make micropython-firmware         # Clone micropython-steami (if needed), link local drivers, build
make micropython-update           # Refresh the MicroPython clone and board-specific submodules
make micropython-deploy           # Flash MicroPython firmware via pyOCD (default)
make micropython-deploy-openocd   # Flash MicroPython firmware via OpenOCD (alternative)
make micropython-deploy-usb       # Flash MicroPython firmware via DAPLink USB mass-storage (alternative)
make micropython-clean            # Clean MicroPython firmware build artifacts
make run SCRIPT=lib/steami_config/examples/show_config.py      # Run with live output
make deploy-script SCRIPT=lib/.../calibrate_magnetometer.py    # Deploy as main.py for autonomous use
make run-main                     # Re-execute main.py on the board
```

The legacy short names (`make firmware`, `make deploy`, etc.) are deprecated and now print an error message asking which firmware (MicroPython or DAPLink) you intended to target.

The MicroPython firmware source is cloned into `.build/micropython-steami/` (gitignored). A symbolic link replaces the submodule `lib/micropython-steami-lib` with your local working directory, so the firmware always includes your latest changes — even uncommitted ones.

Use `make micropython-firmware` for normal rebuilds from the existing local clone. Use `make micropython-update` only when you want to refresh the `micropython-steami` checkout itself or resync the board-specific submodules before rebuilding.

All these tools are included in the dev container. For local development, see the [Prerequisites](#prerequisites) section.

### DAPLink firmware

DAPLink is the firmware running on the STM32F103 interface chip. It provides the USB mass-storage, CMSIS-DAP debug interface, and the I2C bridge used by `daplink_bridge` / `daplink_flash` / `steami_config`.

DAPLink consists of **two parts**:

- **Bootloader** (first stage, flashed at `0x08000000`) — installed once at the factory, rarely updated. It provides the MAINTENANCE mode used to update the interface firmware. Updating it requires an external SWD probe.
- **Interface firmware** (second stage, flashed at `0x08002000`) — contains the I2C bridge, mass-storage, debug interface. Updated routinely, either via the MAINTENANCE USB volume or via an external SWD probe for recovery.

```bash
make daplink-firmware                    # Build the interface firmware (stm32f103xb_steami32_if)
make daplink-bootloader                  # Build the bootloader (stm32f103xb_bl)
make daplink-update                      # Refresh the DAPLink clone
make daplink-clean                       # Clean DAPLink build artifacts

# Routine interface update (no external probe)
make daplink-deploy                      # Alias for daplink-deploy-usb
make daplink-deploy-usb                  # Flash interface firmware via MAINTENANCE volume

# External SWD probe required (recovery, CI, bricked boards)
make daplink-deploy-pyocd                # Flash interface firmware via SWD (pyocd)
make daplink-deploy-openocd              # Flash interface firmware via SWD (openocd)
make daplink-deploy-bootloader           # Flash bootloader via SWD (default: pyocd)
make daplink-deploy-bootloader-pyocd     # Flash bootloader via SWD (pyocd)
make daplink-deploy-bootloader-openocd   # Flash bootloader via SWD (openocd)
```

The DAPLink source is cloned from [steamicc/DAPLink](https://github.com/steamicc/DAPLink) into `.build/DAPLink/` (gitignored). A Python virtualenv is created automatically inside the clone for the progen build tool.

**MAINTENANCE mode (USB path):** power on the board with the RESET button held until a `MAINTENANCE` USB volume appears (instead of the usual `STeaMi` volume). `make daplink-deploy-usb` copies the interface firmware to that volume and the board reboots automatically.

**External SWD probe (bootstrap warning):** the `daplink-deploy-*-pyocd` / `-openocd` and all `daplink-deploy-bootloader*` targets flash the DAPLink chip directly via SWD. They require an **external** probe (ST-Link, J-Link, or another CMSIS-DAP board) connected to the target board's SWD header. **A board cannot reflash its own on-board DAPLink via its own SWD pins** — use another board or a standalone probe. These paths are useful for recovering a bricked interface firmware, installing the bootloader at the factory, or automating CI flashing without manual button presses.

The SWD commands assume an ST-Link probe by default. To use a different probe (another DAPLink board, J-Link, …), override the OpenOCD or pyOCD configuration via `DAPLINK_OPENOCD_INTERFACE`, `DAPLINK_OPENOCD_TRANSPORT`, or `DAPLINK_PYOCD_TARGET` (see `env.mk`).

## Notes

* Keep implementations simple and readable
* Follow existing drivers as reference
* Ensure documentation (`README.md`) and examples are included for each driver
