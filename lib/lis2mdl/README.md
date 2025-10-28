# LIS2MDL Magnetometer Driver for MicroPython

A complete and feature-rich driver for the **LIS2MDL 3-axis magnetometer** by STMicroelectronics.
This library allows easy integration of the LIS2MDL sensor with MicroPython or CircuitPython boards using I²C.
It provides low-level register access, automatic calibration, heading computation, and tilt compensation — ideal for **digital compasses**, **robot navigation**, and **orientation tracking**.

---

## 🧭 Features

* ✅ Full **I²C driver** for LIS2MDL
* ✅ Supports **10 / 20 / 50 / 100 Hz** output data rates
* ✅ **Temperature-compensated** and **low-power** modes
* ✅ Read **raw**, **scaled**, or **calibrated** magnetic field data
* ✅ **2D and 3D calibration** routines (auto min/max method)
* ✅ **Heading computation** (flat or tilt-compensated)
* ✅ **Compass direction labels** (N, NE, E, …)
* ✅ Built-in **digital low-pass filter** and **offset cancellation** control
* ✅ Diagnostic utilities:

  * Register dump
  * Calibration quality metrics
  * Self-test and temperature readout

---

## ⚙️ Hardware Requirements

* **LIS2MDL** 3-axis magnetometer (STMicroelectronics)
* **MicroPython/CircuitPython board**, e.g.:

  * ESP32 / ESP8266
  * Raspberry Pi Pico / RP2040
  * STM32 Nucleo or Pyboard
* 3.3V power supply
* I²C interface (SCL, SDA)

---

## 🔌 Wiring Example (ESP32)

| LIS2MDL Pin | ESP32 Pin | Description  |
| ----------- | --------- | ------------ |
| VIN         | 3.3V      | Power supply |
| GND         | GND       | Ground       |
| SDA         | GPIO21    | I²C Data     |
| SCL         | GPIO22    | I²C Clock    |

Example setup:

```python
from machine import I2C, Pin
from device import LIS2MDL

i2c = I2C(1, scl=Pin(22), sda=Pin(21))
mag = LIS2MDL(i2c)
```

---

## 🧩 Installation

### 1. Copy files to your board

Upload both files using Thonny, mpremote, or ampy:

```
device.py
lis2mdl/const.py
```

### 2. Import and initialize

```python
from machine import I2C, Pin
from device import LIS2MDL

i2c = I2C(1, scl=Pin(22), sda=Pin(21))
mag = LIS2MDL(i2c)
```

---

## 🚀 Quick Start

### Read magnetic field

```python
x, y, z = mag.read_magnet_uT()
print("Magnetic field (µT):", x, y, z)
```

### Get heading (flat orientation)

```python
heading = mag.heading_flat_only()
print("Heading: {:.1f}° {}".format(heading, mag.direction_label(heading)))
```

### With tilt compensation

Requires a function returning accelerometer data `(ax, ay, az)` in g:

```python
def read_accel():
    return (0.0, 0.0, 1.0)  # Example static vector

heading = mag.heading_with_tilt_compensation(read_accel)
```

---

## ⚖️ Calibration

Calibration is essential to obtain accurate compass readings.
The driver provides **automated routines** for both 2D (flat) and 3D calibration.

### 2D Calibration (Flat)

Rotate the board **horizontally** in all directions:

```python
mag.calibrate_minmax_2d(samples=300)
```

### 3D Calibration (Full)

Rotate the board **in all orientations**:

```python
mag.calibrate_minmax_3d(samples=600)
```

### Apply and test calibration

```python
print("Calibration:", mag.read_calibration())
quality = mag.calibrate_quality()
print("Quality metrics:", quality)
```

### Reset calibration

```python
mag.calibrate_reset()
```

---

## 🧰 Configuration Examples

### Output rate and power

```python
mag.set_odr(50)            # 50 Hz
mag.set_low_power(True)    # Enable low-power mode
```

### Enable digital low-pass filter

```python
mag.set_low_pass(True)
```

### Configure declination and heading offset

```python
mag.set_declination(1.5)       # Magnetic declination (°)
mag.set_heading_offset(-5.0)   # Align physical 0°
```

### Block data update (BDU)

```python
mag.set_bdu(True)
```

---

## 🧮 Heading Filtering

You can apply a **smoothing filter** on the heading angle to stabilize the readings:

```python
mag.set_heading_filter(alpha=0.2)  # Light smoothing
```

* `alpha = 0.0` → no filter
* `alpha = 0.1–0.3` → medium smoothing
* `alpha = 1.0` → very heavy smoothing

---

## 🔍 Diagnostics & Debug

### Read sensor ID

```python
print("WHO_AM_I:", hex(mag.read_who_am_i()))
```

Expected value: `0x40`

### Read temperature (approximate)

```python
print("Temperature (°C):", mag.read_temperature_c())
```

### Check data readiness

```python
if mag.data_ready():
    print("New magnetic data available!")
```

### Dump consecutive registers

```python
regs = mag.read_registers(0x60, 12)
print("Register dump:", regs)
```

---

## 🧠 Internal Methods Overview

| Method                             | Description                    |
| ---------------------------------- | ------------------------------ |
| `read_magnet_raw()`                | Raw sensor values (int16)      |
| `read_magnet_uT()`                 | Magnetic field in µT           |
| `read_magnet_calibrated_norm()`    | Calibrated and normalized data |
| `heading_flat_only()`              | Flat compass heading           |
| `heading_with_tilt_compensation()` | Tilt-corrected heading         |
| `read_temperature_c()`             | Read relative temperature      |
| `power_down()` / `wake()`          | Power management               |
| `soft_reset()` / `reboot()`        | Sensor reset functions         |

---

## 🧪 Example: Continuous Compass Loop

```python
from machine import I2C, Pin
from device import LIS2MDL
import time

i2c = I2C(1, scl=Pin(22), sda=Pin(21))
mag = LIS2MDL(i2c)
mag.set_declination(2.3)

while True:
    heading = mag.heading_flat_only()
    print("Heading: {:.1f}° {}".format(heading, mag.direction_label(heading)))
    time.sleep(0.5)
```

---

## 🧾 Notes

* The LIS2MDL outputs magnetic data in **LSB**, with a conversion factor of **0.15 µT/LSB**.
* Temperature readings are **relative only** (not absolute).
* Calibration should be repeated if the sensor environment changes (metal nearby, relocation, etc.).
* Tilt compensation requires an external **accelerometer** or IMU (e.g., LIS3DH, MPU6050, BNO055).

---

## 📚 References

* [STMicroelectronics LIS2MDL Datasheet](https://www.st.com/resource/en/datasheet/lis2mdl.pdf)
* [MicroPython Documentation](https://docs.micropython.org/en/latest/library/machine.I2C.html)

---