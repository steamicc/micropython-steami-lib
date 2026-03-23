# HTS221 MicroPython Driver

MicroPython driver for the **STMicroelectronics HTS221** humidity and temperature sensor.

The HTS221 provides:

* **Relative humidity (%)**
* **Temperature (°C)**

This driver offers a simple and complete API for configuration, measurement, calibration, and power management using **I²C**.

## Features

* I²C communication
* Device identification (`WHO_AM_I`)
* Relative humidity measurement
* Temperature measurement
* One-shot measurement mode
* Continuous measurement mode
* Configurable output data rate (ODR)
* Configurable averaging
* Data-ready status flags
* Power management (power on/off, reboot)
* Built-in factory calibration usage
* User temperature calibration:
  * offset correction
  * two-point calibration

## I²C Address

* Default address: **0x5F** 

## Basic Usage

```python
from machine import I2C
from hts221 import HTS221

# Initialize I2C
i2c = I2C(1)

# Initialize sensor
sensor = HTS221(i2c)

# Read values
humidity = sensor.humidity()
temperature = sensor.temperature()

print("Humidity:", humidity, "%")
print("Temperature:", temperature, "°C")

# Read both at once
h, t = sensor.read()
```

## API

### Device Information

```python
device_id()
```

Returns the sensor device ID (`WHO_AM_I` register).

### Data Readiness

```python
data_ready()
temperature_ready()
humidity_ready()
```

* `data_ready()` → both humidity and temperature available
* `temperature_ready()` → temperature available
* `humidity_ready()` → humidity available

### Measurements

```python
temperature()
humidity()
read()
read_one_shot()
```

* `temperature()` → temperature in °C
* `humidity()` → relative humidity in %
* `read()` → `(humidity, temperature)`
* `read_one_shot()` → performs a one-shot measurement and returns `(humidity, temperature)`

### One-Shot Mode

```python
trigger_one_shot()
```

Triggers a single measurement (used internally by `read_one_shot()`).

### Configuration

```python
get_odr()
set_odr(odr)
set_continuous(odr)
```

* `get_odr()` → returns current output data rate
* `set_odr(odr)` → set ODR (0 = one-shot mode)
* `set_continuous(odr)` → enable continuous mode (ODR ≠ 0)

### Averaging Configuration

```python
get_av()
set_av(av)
```

Controls internal averaging for humidity and temperature.

### Power Management

```python
power_on()
power_off()
reboot()
```

* `power_on()` → enable sensor
* `power_off()` → disable sensor
* `reboot()` → reload calibration data and reboot memory

### Temperature Calibration

```python
set_temp_offset(offset_c)
calibrate_temperature(ref_low, measured_low, ref_high, measured_high)
```

* `set_temp_offset(offset_c)`
  Apply a simple temperature offset correction.

* `calibrate_temperature(...)`
  Perform a **two-point calibration**:

  * improves accuracy
  * adjusts both gain and offset 

## Examples

| File          | Description                            |
| ------------- | -------------------------------------- |
| `humidity.py` | Basic humidity and temperature reading |

Run with:

```bash
mpremote mount lib/htss221 run examples/htss221/examples/humidity.py
```

---

## Notes

* The driver uses **factory calibration data** stored in the sensor.
* Temperature can be further corrected using:

  * `set_temp_offset()` (simple correction)
  * `calibrate_temperature()` (recommended for precision)
* In one-shot mode, the driver automatically waits for data readiness.
* In power-down or one-shot mode, measurements trigger automatically when needed.

---

## Source

This library is a port of:
[https://github.com/jposada202020/MicroPython_HTS221/tree/master](https://github.com/jposada202020/MicroPython_HTS221/tree/master) 
