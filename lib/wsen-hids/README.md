# WSEN-HIDS MicroPython Driver

MicroPython driver for the **Würth Elektronik WSEN-HIDS** humidity and temperature sensor.

The driver provides an easy-to-use API for reading **relative humidity** and **temperature** using the sensor’s **I²C interface**.

The implementation is designed for **MicroPython** and integrates with the **STeaMi ecosystem**.

---

# Features

* I²C communication
* Relative humidity measurement
* Temperature measurement
* One-shot measurement mode
* Continuous measurement mode
* Configurable internal averaging
* Heater control
* Calibration handling
* Data-ready status helpers

---

# Supported Sensor

This driver targets:

**WSEN-HIDS – 2525020210001**

Main characteristics:

| Parameter            | Value             |
| -------------------- | ----------------- |
| Interface            | I²C               |
| Default I²C address  | `0x5F`            |
| Humidity range       | 0–100 %RH         |
| Temperature range    | −40 °C to +120 °C |
| Humidity accuracy    | ±1.8 %RH          |
| Temperature accuracy | ±0.2 °C           |

# Quick Example

```python
from machine import I2C
from time import sleep
from wsen_hids import WSEN_HIDS

i2c = I2C(1)

sensor = WSEN_HIDS(i2c)

while True:
    humidity, temperature = sensor.read()

    print("Humidity: {:.2f} %RH".format(humidity))
    print("Temperature: {:.2f} °C".format(temperature))

    sleep(1)
```

---

# API Overview

## Initialization

```python
sensor = WSEN_HIDS(i2c)
```

Optional parameters:

```python
sensor = WSEN_HIDS(
    i2c,
    address=0x5F,
    check_device=True,
    enable_bdu=True,
)
```

### `device_id()`

Read the device identification register.

```python
sensor.device_id()
```

**Returns:** `int` — Device ID (`WHO_AM_I` register value)


### `enable_bdu(enable=True)`

Enable or disable Block Data Update (BDU).

```python
sensor.enable_bdu(enable=True)
```

When enabled, output registers are not updated until both high and low bytes are read. Recommended to avoid reading inconsistent data.

---

# Reading Measurements

### Combined reading

```python
humidity, temperature = sensor.read()
```

### Humidity only

```python
humidity = sensor.humidity()
```

### Temperature only

```python
temperature = sensor.temperature()
```

---

### Measurement behavior

After initialization, the sensor operates in **one-shot mode** (ODR = 00).
If `read()`, `humidity()`, or `temperature()` are called while the sensor is not in continuous mode, the driver **automatically triggers a one-shot conversion** to ensure fresh data is returned.

```python
humidity, temperature = sensor.read()
```

Continuous measurements can be enabled with:

```python
sensor.set_continuous(WSEN_HIDS.ODR_1_HZ)
```

---

# One-Shot Measurement

Trigger a single conversion:

```python
# Default timeout (100 ms)
humidity, temperature = sensor.read_one_shot()
```

You can specify a timeout:

```python
sensor.read_one_shot(timeout_ms=500)
```

---

# Continuous Measurement Mode

Start continuous measurements:

```python
sensor.set_continuous(WSEN_HIDS.ODR_1_HZ)
```

Available output data rates:

```python
WSEN_HIDS.ODR_ONE_SHOT
WSEN_HIDS.ODR_1_HZ
WSEN_HIDS.ODR_7_HZ
WSEN_HIDS.ODR_12_5_HZ
```

Return to one-shot mode:

```python
sensor.set_one_shot_mode()
```

---

# Averaging Configuration

Configure internal measurement averaging for **temperature and humidity**:

```python
sensor.set_average(avg_t=WSEN_HIDS.AVG_16, avg_h=WSEN_HIDS.AVG_16)
```

Available options:

```
AVG_2
AVG_4
AVG_8
AVG_16
AVG_32
AVG_64
AVG_128
AVG_256
```

**Defaults:**

```python
AVG_T_DEFAULT = AVG_16
AVG_H_DEFAULT = AVG_16
```

**Notes:**

* The same averaging constants (`AVG_*`) are used for both temperature and humidity
* Internally, temperature and humidity are configured in separate registers, but they share identical averaging values
* Higher averaging improves noise performance but increases conversion time

---

# Power Management

The driver provides basic power control methods:

```python
sensor.power_off()
```

Disables the sensor by clearing the PD bit.

```python
sensor.power_on()
```

Re-enables the sensor (restores active mode).

```python
sensor.reboot()
```

Reloads internal memory and calibration data from non-volatile memory.

---

# Heater Control

The sensor contains an internal heater to help remove condensation.

Enable heater:

```python
sensor.enable_heater(True)
```

Disable heater:

```python
sensor.enable_heater(False)
```

Measurements should **not be taken while the heater is active**.

---

# Status Helpers

Check measurement readiness:

```python
sensor.data_ready()
sensor.humidity_ready()
sensor.temperature_ready()
```

These helpers read the **STATUS register** and indicate when fresh data is available.

---

# Calibration

The driver automatically reads the sensor’s **factory calibration coefficients** during initialization and applies the conversion formulas internally.

Additional calibration methods are available:

```python
sensor.set_temp_offset(offset_c)
sensor.calibrate_temperature(ref_low, measured_low, ref_high, measured_high)
```

No calibration is required for basic usage.

---

## Examples

The `examples/` directory provides practical scripts demonstrating how to use the WSEN-HIDS sensor in different scenarios.

### Overview

| Example | Description |
|--------|------------|
| `one_shot_mode.py` | Basic one-shot measurements: trigger a measurement and read humidity and temperature on demand |
| `continuous_mode.py` | Continuous measurement mode: sensor runs continuously and values are read periodically |
| `humidity_temperature.py` | Beginner-friendly example: perform a single read and print humidity and temperature |
| `comfort_monitor.py` | Read every 2 seconds and display a comfort indicator (`Dry`, `Comfortable`, `Humid`) based on humidity |
| `data_logger.py` | Log data every 5 seconds in CSV format (`timestamp, humidity, temperature`) for serial capture |
| `dew_point.py` | Compute and display dew point using temperature and humidity (Magnus formula) |
| `heater_demo.py` | Demonstrate the built-in heater: compare readings before and after enabling it |
| `low_power_sampling.py` | Low-power sampling: one-shot every 10 s with `power_off()` between reads. Requires firmware >= v0.1.0 (#238) |
