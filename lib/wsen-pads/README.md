# WSEN-PADS MicroPython Driver

MicroPython driver for the **Würth Elektronik WSEN-PADS** absolute pressure sensor.

This driver provides an easy-to-use API to read **pressure** and **temperature** using the I²C interface.

The WSEN-PADS is a high-resolution digital pressure sensor with integrated temperature measurement, designed for applications such as weather monitoring, altimetry, and environmental sensing.

---

# Features

* I²C communication
* Pressure measurement
* Temperature measurement
* One-shot acquisition
* Continuous measurement mode
* Configurable Output Data Rate (ODR)
* Low-noise mode support
* Optional low-pass filter
* Soft reset and device reboot
* Raw data access

---

# Sensor Overview

| Feature                 | Value                  |
| ----------------------- | ---------------------- |
| Pressure range          | 26 kPa – 126 kPa       |
| Pressure resolution     | 24-bit                 |
| Temperature resolution  | 16-bit                 |
| Pressure sensitivity    | 1 / 4096 hPa per digit |
| Temperature sensitivity | 0.01 °C per digit      |
| Interface               | I²C / SPI              |
| Maximum ODR             | 200 Hz                 |

---

# Hardware Connection

The driver currently supports **I²C mode**.

## Pins

| Sensor Pin | Description          |
| ---------- | -------------------- |
| VDD        | Power supply         |
| VDD_IO     | Interface supply     |
| GND        | Ground               |
| SDA        | I²C data             |
| SCL        | I²C clock            |
| CS         | Must be HIGH for I²C |
| SAO        | Selects I²C address  |

## I²C Address

| SAO  | Address |
| ---- | ------- |
| LOW  | `0x5C`  |
| HIGH | `0x5D`  |

Recommended configuration for a single device on the bus:

```
SAO = HIGH
I2C address = 0x5D
```

---

# Installation

Clone the repository and copy the driver to your MicroPython device.

Example using **mpremote**:

```bash
mpremote mount lib/wsen-pads
```

The driver will then be available as:

```python
from wsen_pads import WSEN_PADS
```

---

# Basic Usage

```python
from machine import I2C, Pin
from time import sleep
from wsen_pads import WSEN_PADS

i2c = I2C(
    1,
    scl=Pin(7),
    sda=Pin(6),
)

sensor = WSEN_PADS(i2c)

while True:
    pressure, temperature = sensor.read()

    print("Pressure:", pressure, "hPa")
    print("Temperature:", temperature, "°C")
    print()

    sleep(1)
```

---

# One-shot Measurement

```python
pressure, temperature = sensor.read_one_shot()
```

This triggers a single conversion and returns the measurement.

---

# Continuous Mode

```python
from wsen_pads.const import ODR_10_HZ

sensor.set_continuous(odr=ODR_10_HZ)

pressure = sensor.pressure()
temperature = sensor.temperature()
```

Available ODR values:

```
ODR_1_HZ
ODR_10_HZ
ODR_25_HZ
ODR_50_HZ
ODR_75_HZ
ODR_100_HZ
ODR_200_HZ
```

---

# Raw Data Access

Raw values from the sensor can also be read:

```python
raw_pressure = sensor.pressure_raw()
raw_temperature = sensor.temperature_raw()
```

Conversions:

```
pressure_hpa = raw_pressure / 4096
temperature_c = raw_temperature * 0.01
```

---

# Status Helpers

The driver provides helper functions for checking data availability.

```python
sensor.pressure_available()
sensor.temperature_available()
sensor.is_ready()
```

---

# Device Control

## Soft Reset

```python
sensor.soft_reset()
```

## Reboot Sensor

```python
sensor.reboot()
```

---

# Examples

Examples are available in the `examples` directory.

---

# Driver Structure

```
wsen-pads/
│
├── README.md
├── manifest.py
├── examples/
│
└── wsen_pads/
    ├── __init__.py
    ├── const.py
    ├── device.py
    └── exceptions.py
```

---
