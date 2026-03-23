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
from machine import I2C, Pin
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

Configure internal measurement averaging:

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

Higher averaging improves noise performance but increases conversion time.

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

⚠️ Measurements should **not be taken while the heater is active**.

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

# Examples

Example scripts are located in:

```
examples/
```

Examples include:

* basic one-shot measurements
* continuous measurement mode
* driver validation tests
