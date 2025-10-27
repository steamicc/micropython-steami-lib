# LIS2MDL Magnetometer Driver

This is a MicroPython driver for the LIS2MDL 3-axis magnetometer. The LIS2MDL is a high-performance magnetic sensor designed for applications such as electronic compasses, motion tracking, and orientation detection. This driver provides methods for initialization, calibration, and reading magnetic field data.

## Features
- Soft reset and initialization of the LIS2MDL sensor.
- Configurable output data rate (ODR) and low-power mode.
- 3D calibration for offsets and scales.
- Heading calculation with and without tilt compensation.
- Direction labeling (e.g., N, NE, E, etc.).

## Requirements
- MicroPython-compatible board with I2C support.
- LIS2MDL sensor module.

## Installation
1. Copy the `lis2mdl` folder to your MicroPython device.
2. Import the driver in your script:
   ```python
   from lis2mdl.device import LIS2MDL
   ```

## Usage
### Basic Example
```python
from time import sleep_ms
from machine import I2C
from lis2mdl.device import LIS2MDL

# Initialize I2C and LIS2MDL
i2c = I2C(1)
mag = LIS2MDL(i2c)

# Perform calibration
mag.calibrate_step()
calibration_values = mag.get_calibration()
print("Calibration values:", calibration_values)

# Continuous heading reading
print("Continuous heading readings:")
while True:
    angle = mag.heading_flat_only()
    direction = mag.direction_label(angle)
    print(f"{direction} | angle={angle:.2f}°")
    sleep_ms(100)
```

### Tilt Compensation Example
To use tilt compensation, you need an accelerometer to provide roll and pitch data. Pass a function that reads accelerometer data to the `heading_with_tilt_compensation` method.

```python
def read_accel():
    # Replace with your accelerometer reading logic
    return ax, ay, az

angle = mag.heading_with_tilt_compensation(read_accel)
print(f"Tilt-compensated angle: {angle:.2f}°")
```

## Calibration
The `calibrate_step` method performs a quick 3D calibration. Rotate the sensor flat over 360° to capture the minimum and maximum magnetic field values. The offsets and scales are calculated automatically.

## Datasheet
For detailed information about the LIS2MDL sensor, refer to the [datasheet](https://www.st.com/resource/en/datasheet/lis2mdl.pdf).

## Notes
- The `heading_with_tilt_compensation` method has not been tested due to the lack of an accelerometer during development.
- Ensure the I2C pins are correctly connected to the LIS2MDL module.