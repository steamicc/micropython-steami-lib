# VL53L1X MicroPython Driver

MicroPython driver for the **VL53L1X Time-of-Flight (ToF) distance sensor**.

This library is a port of the original MicroPython VL53L1X driver. 

## Features

* Time-of-Flight **distance measurement**
* Distance reading in **millimeters**
* **Model ID verification** on initialization
* Start / stop ranging control
* Data-ready polling
* Power management:

  * power on / off
  * software reset
* Continuous measurement support

## Sensor Specifications

| Feature       | Value                |
| ------------- | -------------------- |
| Technology    | Time-of-Flight (ToF) |
| Range         | Up to ~4 meters      |
| Accuracy      | ± few mm (typical)   |
| Field of View | ~27°                 |
| Interface     | I²C                  |

## I2C Address

Default I²C address:

```
0x29
```

## Basic Usage

```python
from machine import I2C
from vl53l1x import VL53L1X

# Init I2C
i2c = I2C(1)

# Init sensor
tof = VL53L1X(i2c)

# Read distance (mm)
distance = tof.read()

print("Distance:", distance, "mm")
```

## API Reference

### Initialization

```python
VL53L1X(i2c, address=0x29)
```

### Measurement

* `read()` — read distance in millimeters
* `distance_mm()` — same as `read()`

### Ranging Control

* `start_ranging()` — start continuous ranging
* `stop_ranging()` — stop ranging
* `data_ready()` — check if new data is available

### Device Control

* `device_id()` — read sensor model ID
* `reset()` — software reset

### Power Management

* `power_on()` — power up sensor
* `power_off()` — power down sensor

## Examples

Examples are available in the `examples/` folder:

| File        | Description                |
| ----------- | -------------------------- |
| distance.py | Basic distance measurement |

Run an example with:

```bash
mpremote mount lib/vl53l1x run lib/vl53l1x/examples/distance.py
```

## Notes

* The sensor requires **initialization time after power-on** (~200 ms).
* The driver automatically checks the **device ID (0xEACC)** during initialization and raises an error if the sensor is not detected. 
* Distance measurements are returned in **millimeters**.
* The driver waits for data readiness internally before returning a measurement.

## Source

This library is a port of:

[https://github.com/drakxtwo/vl53l1x_pico](https://github.com/drakxtwo/vl53l1x_pico) 
