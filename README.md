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
| DAPLink Flash | [`daplink_flash`](lib/daplink_flash/README.md) | `0x3B`      | I2C-to-SPI flash bridge + config zone |
| SSD1327       | [`ssd1327`](lib/ssd1327/README.md)             | — (SPI)     | 128x128 greyscale OLED display        |
| MCP23009E     | [`mcp23009e`](lib/mcp23009e/README.md)         | `0x20`      | 8-bit I/O expander (D-PAD)            |
| VL53L1X       | [`vl53l1x`](lib/vl53l1x/README.md)             | `0x29`      | Time-of-Flight distance sensor        |
| APDS-9960     | [`apds9960`](lib/apds9960/README.md)           | `0x39`      | Proximity, gesture, color, light      |
| HTS221        | [`hts221`](lib/hts221/README.md)               | `0x5F`      | Humidity + temperature                |
| WSEN-HIDS     | [`wsen-hids`](lib/wsen-hids/README.md)         | `0x5F`      | Humidity + temperature                |
| WSEN-PADS     | [`wsen-pads`](lib/wsen-pads/README.md)         | `0x5D`      | Pressure + temperature                |
| ISM330DL      | [`ism330dl`](lib/ism330dl/README.md)           | `0x6B`      | 6-axis IMU (accel + gyro)             |
| LIS2MDL       | [`lis2mdl`](lib/lis2mdl/README.md)             | `0x1E`      | 3-axis magnetometer                   |
| IM34DT05      | [`im34dt05`](lib/im34dt05/README.md)           | — (PDM)     | Digital microphone                    |
| BME280        | [`bme280`](lib/bme280/README.md)               | `0x76`      | Pressure + humidity + temperature     |
| GC9A01        | [`gc9a01`](lib/gc9a01/README.md)               | — (SPI)     | Round color LCD display               |
| STeaMi Config | [`steami_config`](lib/steami_config/README.md) | —           | Persistent board configuration        |


## Quick start
Use mpremote to quickly run a driver example without installing anything on the board.

```bash
pip install mpremote
mpremote mount lib/ism330dl run lib/ism330dl/examples/basic_read.py
```

This mounts the driver temporarily and executes an example directly on the STeaMi board.

## Installation

### Method 1: Using mpremote (temporary)

Use this method during development to run drivers without copying them to the board. (recommended for development)

```bash
mpremote mount lib/<driver_folder>/<driver> run lib/<driver_folder>/examples/<driver_example>
```

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

## Testing

Run the full mock test suite:

```bash
python -m pytest tests/ -v -k mock
```

See full details in [tests/TESTING.md](tests/TESTING.md)
## Contributing

Contributions are welcome! Please follow the project guidelines.

See [CONTRIBUTING.md](CONTRIBUTING.md)

## License

This project is licensed under the [GPL v3](LICENSE) License. See the LICENSE file for more details.

## Additional Resources

- [STeaMi Official Website](https://www.steami.cc/)
- [MicroPython Documentation](https://docs.micropython.org/)
- [mpremote Documentation](https://docs.micropython.org/en/latest/reference/mpremote.html)
