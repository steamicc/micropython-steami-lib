# VL53L1X MicroPython Driver

MicroPython driver for the **VL53L1X Time-of-Flight (ToF) distance sensor**.

This library is a port of [vl53l1x_pico](https://github.com/drakxtwo/vl53l1x_pico).

## Supported Sensor

| Feature              | Value                |
| -------------------- | -------------------- |
| Technology           | Time-of-Flight (ToF) |
| Range                | Up to ~4 meters      |
| Accuracy             | ± 3% (typical)       |
| Field of View        | 27°                  |
| Interface            | I²C                  |
| Default I²C address  | `0x29`               |
| Device ID            | `0xEACC`             |

## Features

* Time-of-Flight distance measurement in millimeters
* Model ID verification on initialization
* Start / stop ranging control
* Data-ready polling
* Power management (on/off, reset)
* Continuous measurement support

## Basic Usage

```python
from machine import I2C
from vl53l1x import VL53L1X

i2c = I2C(1)
tof = VL53L1X(i2c)

distance = tof.read()
print("Distance:", distance, "mm")
```

## API Reference

### Initialization

```python
tof = VL53L1X(i2c, address=0x29)
```

The constructor checks the device ID (`0xEACC`) and raises `OSError` if the sensor is not detected.

### Measurement

* `distance_mm()` — read distance in millimeters (triggers ranging if needed)
* `read()` — alias for `distance_mm()`

### Ranging Control

* `start_ranging()` — start continuous ranging
* `stop_ranging()` — stop ranging
* `data_ready()` — check if new data is available

### Device Control

* `device_id()` — read sensor model ID (returns `0xEACC`)
* `reset()` — hardware reset via SOFT_RESET register (takes ~100 ms)

### Power Management

* `power_on()` — power up sensor
* `power_off()` — power down sensor

## Examples

| File          | Description                         |
| ------------- | ----------------------------------- |
| `distance.py` | Continuous distance measurement loop |

```bash
mpremote mount lib/vl53l1x run lib/vl53l1x/examples/distance.py
```

## Notes

* The sensor requires initialization time after power-on (~200 ms).
* The driver automatically waits for data readiness before returning a measurement.
* Distance measurements are returned in millimeters.
