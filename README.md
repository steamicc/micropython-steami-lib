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
│   ├── ism330dlc/      # Accelerometer and gyroscope ISM330DLCTR
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

### ISM330DLCTR (Accelerometer and Gyroscope)

The ISM330DLCTR is a 6DOF inertial module integrating accelerometer and gyroscope.

#### Mounting and Running an Example

```bash
# Mount the driver and run the example
mpremote mount lib/ism330dlc run lib/ism330dlc/examples/imu_reading.py
```

#### Basic API

```python
from ism330dlc import ISM330DLC

# Initialization
i2c = machine.I2C(1)
imu = ISM330DLC(i2c)

# Reading values
accel_x, accel_y, accel_z = imu.read_accel()
gyro_x, gyro_y, gyro_z = imu.read_gyro()

# Configuration
imu.set_accel_odr(ISM330DLC.ACCEL_ODR_104HZ)
imu.set_gyro_odr(ISM330DLC.GYRO_ODR_104HZ)
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

apds.enableLightSensor()
light = apds.readAmbientLight()

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

## Contributing

Contributions are welcome! Here's how you can contribute:

1. Fork the repository
2. Create a branch for your feature (`git checkout -b my-new-feature`)
3. Commit your changes (`git commit -am 'Add a new feature'`)
4. Push to the branch (`git push origin my-new-feature`)
5. Create a new Pull Request

## License

This project is licensed under the [GPL v3](LICENSE) License. See the LICENSE file for more details.

## Additional Resources

- [STeaMi Official Website](https://www.steami.cc/)
- [MicroPython Documentation](https://docs.micropython.org/)
- [mpremote Documentation](https://docs.micropython.org/en/latest/reference/mpremote.html)
