# micropython-steami-lib

This repository contains all the drivers for the main components of the [STeaMi](https://www.steami.cc/) board. These drivers are written for MicroPython and are designed to be used either in the construction of the official MicroPython firmware for the STeaMi board or independently for custom projects.

## Repository Contents

The repository is organized as follows:

```
micropython-steami-lib/
├── lib/                # Drivers for the different components
│   ├── bq27441/        # Battery gauge BQ27441-G1
│   │   ├── README.md   # Component-specific documentation
│   │   ├── manifest.py # Manifest file for firmware inclusion
│   │   ├── bq27441/    # Driver source code
│   │   └── examples/   # Usage examples
│   ├── w2564jv/        # SPI flash memory W2564JV-DTR
│   ├── ssd1327/        # OLED display controller SSD1327ZB
│   ├── mcp23009/       # I2C I/O expander MCP23009
│   ├── vl53l1cx/       # Distance sensor VL53L1CX
│   ├── apds9960/       # Gesture and color sensor APDS-9960
│   ├── wsen_hids/      # Humidity sensor WSEN-HIDS 2525020210001
│   ├── ism330dl/       # Accelerometer and gyroscope ISM330DL
│   ├── lis2mdl/        # Magnetometer LIS2MDLTR
│   ├── wsen_pads/      # Pressure sensor WSEN-PADS 25110202133011
│   ├── im34dt05/       # Digital microphone IM34DT05
├── LICENSE             # Project license
└── README.md           # This file
```

## Installation

### Method 1: Using mpremote

To use the drivers without permanent installation, you can use `mpremote` to mount the desired driver on your STeaMi board and run examples.

1. Make sure you have installed `mpremote`:

   ```bash
   pip install mpremote
   ```

2. Connect your STeaMi board to your computer via USB.

3. Mount the driver and run an example (see the specific section for each driver below).

### Method 2: Permanent Installation

If you want to permanently install the drivers on your board:

```bash
mpremote cp -r lib/<driver>/<driver_folder> :lib/
```

For example, to install the SSD1327 display driver:

```bash
mpremote cp -r lib/ssd1327/ssd1327 :lib/
```

## Using the Drivers

Here's the documentation for each driver available in this repository:

### BQ27441-G1 (Battery Gauge)

The BQ27441-G1 is a precision battery gauge that monitors battery status.

#### Mounting and Running an Example

```bash
# Mount the driver and run the example
mpremote mount lib/bq27441 run lib/bq27441/examples/fuel_gauge.py
```

#### Basic API

```python
from bq27441 import BQ27441

# Initialization with default I2C
i2c = machine.I2C(0)
bq = BQ27441(i2c)

# Reading battery information
bq.state_of_charge() # State of charge in %
bq.voltage() # Voltage in mV
bq.current_average() # Average current discharge in mA
bq.capacity_full() # Full capacity in mAh
bq.capacity_remaining() # Remaining capacity in mAh
```

### W2564JV-DTR (SPI Flash Memory)

The W2564JV-DTR is a 64 Mbit SPI flash memory.

#### Mounting and Running an Example

```bash
# Mount the driver and run the example
mpremote mount lib/w2564jv run lib/w2564jv/examples/flash_read_write.py
```

#### Basic API

```python
from w2564jv import W2564JV

# Initialization with SPI
spi = machine.SPI(0)
cs = machine.Pin(5, machine.Pin.OUT)
flash = W2564JV(spi, cs)

# Reading and writing
data = b'Hello, STeaMi!'
flash.write(0, data)
read_data = flash.read(0, len(data))
```

### SSD1327ZB (OLED Display Controller)

The SSD1327ZB is a monochrome OLED display controller.

#### Mounting and Running an Example

```bash
# Mount the driver and run the example
mpremote mount lib/ssd1327 run lib/ssd1327/examples/helloworld.py
```

#### Basic API

```python
from ssd1327 import SSD1327

# Initialization
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)

# Display
display.fill(0)                # Clear the screen
display.text("STeaMi", 0, 0)   # Display text
display.show()                 # Update the display
```

### MCP23009 (I2C I/O Expander)

The MCP23009 is an 8-bit I/O expander with I2C interface.

#### Mounting and Running an Example

```bash
# Mount the driver and run the example
mpremote mount lib/mcp23009 run lib/mcp23009/examples/gpio_control.py
```

#### Basic API

```python
from mcp23009 import MCP23009

# Initialization
i2c = machine.I2C(1)
mcp = MCP23009(i2c)

# Pin configuration and control
mcp.setup(0, MCP23009.OUT)     # Configure pin 0 as output
mcp.output(0, 1)               # Set pin 0 high
mcp.setup(1, MCP23009.IN)      # Configure pin 1 as input
value = mcp.input(1)           # Read pin 1 state
```

### VL53L1CX (ToF Distance Sensor)

The VL53L1CX is a precision time-of-flight (ToF) distance sensor.

#### Mounting and Running an Example

```bash
# Mount the driver and run the example
mpremote mount lib/vl53l1cx run lib/vl53l1cx/examples/distance.py
```

#### Basic API

```python
from vl53l1cx import VL53L1CX

# Initialization
i2c = machine.I2C(1)
tof = VL53L1CX(i2c)

# Configuration and measurement
distance = tof.read()  # Distance in mm

```

### ISM330DL (Accelerometer and Gyroscope)

The ISM330DL is a 6DOF inertial module integrating accelerometer and gyroscope.

#### Mounting and Running an Example

```bash
# Mount the driver and run the example
mpremote mount lib/ism330dl run lib/ism330dl/examples/basic_read.py
```

#### Basic API

```python
from ism330dl import ISM330DL

# Initialization
i2c = machine.I2C(1)
imu = ISM330DL(i2c)

# Reading values
ax, ay, az = imu.acceleration_g()
gx, gy, gz = imu.gyroscope_dps()
temp = imu.temperature_c()

# Configuration
from ism330dl.const import ACCEL_ODR_104HZ, ACCEL_FS_4G
imu.configure_accel(ACCEL_ODR_104HZ, ACCEL_FS_4G)
```

### APDS-9960 (Gesture and Color Sensor)

The APDS-9960 is a proximity, gesture, color, and ambient light sensor.

#### Mounting and Running an Example

```bash
# Mount the driver and run the example
mpremote mount lib/apds9960 run lib/apds9960/examples/ambient_light.py
```

#### Basic API

```python
from apds9960 import APDS9960

# Initialization
i2c = machine.I2C(1)
apds = APDS9960(i2c)

apds.enable_light_sensor()
light = apds.read_ambient_light()

```

### WSEN-HIDS (Humidity Sensor)

The WSEN-HIDS 2525020210001 is a high-precision humidity and temperature sensor.

#### Mounting and Running an Example

```bash
# Mount the driver and run the example
mpremote mount lib/wsen_hids run lib/wsen_hids/examples/humidity.py
```

#### Basic API

```python
from wsen_hids import WSEN_HIDS

# Initialization
i2c = machine.I2C(1)
hids = WSEN_HIDS(i2c)

# Reading values
humidity = hids.humidity()      # Relative humidity in %
temperature = hids.temperature() # Temperature in °C
```

### LIS2MDLTR (Magnetometer)

The LIS2MDLTR is a high-precision 3-axis magnetometer.

#### Mounting and Running an Example

```bash
# Mount the driver and run the example
mpremote mount lib/lis2mdl run lib/lis2mdl/examples/compass.py
```

#### Basic API

```python
from lis2mdl import LIS2MDL

# Initialization
i2c = machine.I2C(1)
mag = LIS2MDL(i2c)

# Reading values
mag_x, mag_y, mag_z = mag.read_mag()

# Configuration
mag.set_data_rate(LIS2MDL.DATA_RATE_10HZ)
```

### WSEN-PADS (Pressure Sensor)

The WSEN-PADS 25110202133011 is a high-precision pressure and temperature sensor.

#### Mounting and Running an Example

```bash
# Mount the driver and run the example
mpremote mount lib/wsen_pads run lib/wsen_pads/examples/pressure.py
```

#### Basic API

```python
from wsen_pads import WSEN_PADS

# Initialization
i2c = machine.I2C(1)
pads = WSEN_PADS(i2c)

# Reading values
pressure = pads.pressure()       # Pressure in hPa
temperature = pads.temperature() # Temperature in °C
```

### IM34DT05 (Digital Microphone)

The IM34DT05 is a MEMS digital microphone with PDM interface.

#### Mounting and Running an Example

```bash
# Mount the driver and run the example
mpremote mount lib/im34dt05 run lib/im34dt05/examples/sound_level.py
```

#### Basic API

```python
from im34dt05 import IM34DT05

# Initialization
clock_pin = machine.Pin(MIC_CLK, machine.Pin.OUT)
data_pin = machine.Pin(MIC_IN, machine.Pin.IN)
mic = IM34DT05(clock_pin, data_pin)

# Audio acquisition
mic.start()
samples = mic.read_samples(1024)
mic.stop()

# Audio processing
level = mic.sound_level(samples)  # Sound level in dB
```

## Testing

The project includes a test framework that supports both mock tests (without hardware) and hardware tests (with a STeaMi board connected).

### Install test dependencies

```bash
pip install pytest pyyaml
```

### Run mock tests (no hardware needed)

```bash
python -m pytest tests/ -v -k mock
```

### Run hardware tests (STeaMi board connected)

```bash
python -m pytest tests/ -v --port /dev/ttyACM0
```

### Run tests for a specific driver

```bash
python -m pytest tests/ -v --driver hts221 --port /dev/ttyACM0
```

### Run interactive tests (with manual validation)

```bash
python -m pytest tests/ -v --port /dev/ttyACM0 -s
```

### Generate a test report

Reports are saved as Markdown files in the `reports/` directory, with a summary and a detailed sub-report per driver.

```bash
# Timestamped report
python -m pytest tests/ -v --port /dev/ttyACM0 --report auto

# Named report (e.g. before a release)
python -m pytest tests/ -v --port /dev/ttyACM0 --report v1.0-validation
```

### Add tests for a new driver

Create a YAML scenario file in `tests/scenarios/<driver>.yaml`:

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

## Contributing

Contributions are welcome! Please follow the guidelines below.

### Driver structure

Each driver must follow this structure:

```
lib/<component>/
├── README.md
├── manifest.py          # metadata() + package("<module_name>")
├── <module_name>/
│   ├── __init__.py      # exports main class
│   ├── const.py         # register constants using micropython.const()
│   └── device.py        # main driver class
└── examples/
    └── *.py
```

### Coding conventions

- **Constants**: use `from micropython import const` wrapper in `const.py` files.
- **Naming**: `snake_case` for all methods and variables. Enforced by ruff (N802, N803, N806).
- **Class inheritance**: `class Foo(object):` is the existing convention.
- **Time**: use `from time import sleep_ms` (not `utime`, not `sleep()` with float seconds).
- **Exceptions**: use `except Exception:` instead of bare `except:`.
- **No debug `print()`** in production driver code.

### Driver API conventions

- **Constructor signature**: `def __init__(self, i2c, ..., address=DEFAULT_ADDR)` — first parameter is always `i2c` (not `bus`), address uses keyword argument with a default from `const.py`.
- **Attributes**: `self.i2c` for the I2C bus, `self.address` for the device address (not `self.bus`, `self.addr`).
- **I2C helpers**: use private snake_case methods `_read_reg()`, `_write_reg()` for register access.
- **Device identification**: `device_id()` — returns the device/WHO_AM_I register value. All I2C drivers with an ID register must implement this method.

### Linting

The project uses [ruff](https://docs.astral.sh/ruff/) (config in `pyproject.toml`).

```bash
# Check for linting errors
ruff check

# Auto-format code
ruff format
```

### Commit messages

Commit messages are validated by CI with the following pattern:

```
<scope>: <Description starting with a capital letter ending with a period.>
```

- Max 78 characters.
- Examples:
  - `hts221: Fix missing self parameter in getAv method.`
  - `docs: Fix typos in README files.`
  - `bq27441: Remove debug print statements from driver.`

### CI checks

All pull requests must pass these checks:

| Check | Workflow | Description |
|-------|----------|-------------|
| Commit messages | `check-commits.yml` | Validates commit message format |
| Linting | `python-linter.yml` | Runs `ruff check` |
| Mock tests | `tests.yml` | Runs mock driver tests |

### Workflow

1. Fork the repository
2. Create a branch for your feature (`git checkout -b feat/my-new-feature`)
3. Write your code and add tests in `tests/scenarios/<driver>.yaml`
4. Run `ruff check` and `python -m pytest tests/ -v -k mock` locally
5. Commit your changes following the commit message format
6. Push to the branch and create a Pull Request

## License

This project is licensed under the [GPL v3](LICENSE) License. See the LICENSE file for more details.

## Additional Resources

- [STeaMi Official Website](https://www.steami.cc/)
- [MicroPython Documentation](https://docs.micropython.org/)
- [mpremote Documentation](https://docs.micropython.org/en/latest/reference/mpremote.html)
