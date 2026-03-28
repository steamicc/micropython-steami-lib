# micropython-steami-lib

This repository contains all the drivers for the main components of the [STeaMi](https://www.steami.cc/) board. These drivers are written for MicroPython and are designed to be used either in the construction of the official MicroPython firmware for the STeaMi board or independently for custom projects.

## Repository contents

* Ready-to-use **MicroPython drivers**
* Consistent **API design across all components**
* Full **mock + hardware test suite**
* CI integration for reliability

## Board components

| Component     | Driver                                         | I2C Address | Description                           |
| ------------- | ---------------------------------------------- | ----------- | ------------------------------------- |
| BQ27441-G1    | [`bq27441`](lib/bq27441/README.md)             | `0x55`      | Battery fuel gauge                    |
| DAPLink Bridge | [`daplink_bridge`](lib/daplink_bridge/)        | `0x3B`      | I2C bridge to STM32F103 + config zone |
| DAPLink Flash | [`daplink_flash`](lib/daplink_flash/README.md) | —           | Flash file operations via bridge      |
| SSD1327       | [`ssd1327`](lib/ssd1327/README.md)             | — (SPI)     | 128x128 greyscale OLED display        |
| MCP23009E     | [`mcp23009e`](lib/mcp23009e/README.md)         | `0x20`      | 8-bit I/O expander (D-PAD)            |
| VL53L1X       | [`vl53l1x`](lib/vl53l1x/README.md)             | `0x29`      | Time-of-Flight distance sensor        |
| APDS-9960     | [`apds9960`](lib/apds9960/README.md)           | `0x39`      | Proximity, gesture, color, light      |
| HTS221        | [`hts221`](lib/hts221/README.md)               | `0x5F`      | Humidity + temperature                |
| WSEN-HIDS     | [`wsen-hids`](lib/wsen-hids/README.md)         | `0x5F`      | Humidity + temperature                |
| WSEN-PADS     | [`wsen-pads`](lib/wsen-pads/README.md)         | `0x5D`      | Pressure + temperature                |
| ISM330DL      | [`ism330dl`](lib/ism330dl/README.md)           | `0x6B`      | 6-axis IMU (accel + gyro)             |
| LIS2MDL       | [`lis2mdl`](lib/lis2mdl/README.md)             | `0x1E`      | 3-axis magnetometer                   |
| IM34DT05      | `im34dt05` *(not yet implemented)*              | — (PDM)     | Digital microphone                    |
| BME280        | `bme280` *(not yet implemented)*                | `0x76`      | Pressure + humidity + temperature     |
| GC9A01        | `gc9a01` *(not yet implemented)*                | — (SPI)     | Round color LCD display               |
| STeaMi Config | [`steami_config`](lib/steami_config/README.md) | —           | Persistent board configuration        |


## Quick start

Run a driver example on your STeaMi board without installing anything permanently.

### Prerequisites

* A STeaMi board running MicroPython
* A USB cable to connect the board to your computer
* Python installed on your computer

### 1. Install `mpremote`

`mpremote` is the official MicroPython tool to interact with your board.

```bash
pip install mpremote
```

### 2. Connect your board

Plug your STeaMi board via USB.

To verify that it is detected:

```bash
mpremote connect list
```

You should see a serial device (e.g. `/dev/ttyUSB0` on Linux or `COM3` on Windows).


### 3. Run an example

You can run a driver example directly on the board without copying files:

```bash
mpremote mount lib/ism330dl run lib/ism330dl/examples/basic_read.py
```

## Installation

### Method 1: Using mpremote (recommended for development)

The Quick start section above shows how to run examples temporarily. The `mount` command makes the driver available without copying it to the board.

### Method 2: Permanent installation (copy to board)

Install a driver permanently by copying it into the board’s /lib directory.

```bash
mpremote cp -r lib/<driver_folder>/<driver> :lib/
```

Example:

```bash
mpremote cp -r lib/ssd1327/ssd1327 :lib/
```

Once copied, the driver can be imported normally without mounting.

## Development

### Setup

```bash
make setup    # Install pip + npm dependencies and git hooks
```

### Available commands

Run `make help` to see all available targets:

| Command | Description |
|---------|-------------|
| `make lint` | Run ruff linter |
| `make lint-fix` | Auto-fix lint issues |
| `make test` | Run mock tests (no hardware) |
| `make test-mock` | Run mock tests |
| `make test-hardware` | Run all hardware tests (needs board) |
| `make test-board` | Board tests only (buttons, LEDs, buzzer) |
| `make test-sensors` | Sensor driver hardware tests |
| `make test-all` | All tests (mock + hardware) |
| `make test-examples` | Validate example files |
| `make test-<scenario>` | Test a specific scenario (e.g. `make test-hts221`) |
| `make ci` | Full CI pipeline (lint + tests + examples) |
| `make repl` | Open MicroPython REPL |
| `make mount` | Mount lib/ on the board |
| `make clean` | Remove caches |
| `make deepclean` | Remove everything including node_modules |

Per-scenario targets are generated automatically from `tests/scenarios/*.yaml`.

### Git hooks

Git hooks are managed by [husky](https://typicode.github.io/husky/) and run automatically on commit:

- **commit-msg** — validates commit message format via [commitlint](https://commitlint.js.org/)
- **pre-commit** — branch name validation, content checks (conflict markers, TODO), ruff on staged `.py` files

### Testing

Run the full mock test suite:

```bash
make test
```

Run hardware tests (requires a STeaMi board on `/dev/ttyACM0`):

```bash
make test-hardware
```

Run tests for a specific driver:

```bash
make test-hts221
```

See full details in [tests/TESTING.md](tests/TESTING.md).

## Contributing

Contributions are welcome! Please follow the project guidelines.

See [CONTRIBUTING.md](CONTRIBUTING.md)

## License

This project is licensed under the [GPL v3](LICENSE) License. See the LICENSE file for more details.

## Additional Resources

- [STeaMi Official Website](https://www.steami.cc/)
- [MicroPython Documentation](https://docs.micropython.org/)
- [mpremote Documentation](https://docs.micropython.org/en/latest/reference/mpremote.html)
