# ISM330DL MicroPython Driver

MicroPython driver for the **STMicroelectronics ISM330DL** 6-axis IMU.

The ISM330DL integrates:

* a **3-axis accelerometer**
* a **3-axis gyroscope**

This driver provides a simple API to configure the sensor and read motion data using **I²C**.

---

# Features

* I²C communication
* device identification (`WHO_AM_I`)
* accelerometer configuration
* gyroscope configuration
* raw sensor readings
* converted physical units
* board orientation reading
* board rotation reading
* temperature reading
* data-ready status helpers
* power-down mode

---

# Sensor overview

| Sensor        | Range                              | Unit      |
| ------------- | ---------------------------------- | --------- |
| Accelerometer | ±2g / ±4g / ±8g / ±16g             | g         |
| Gyroscope     | ±125 / ±250 / ±500 / ±1000 / ±2000 | degrees/s |
| Temperature   | internal sensor                    | °C        |

---

# I²C Address

The sensor can use two I²C addresses depending on the **SA0 pin**:

| SA0 | Address |
| --- | ------- |
| 0   | `0x6A`  |
| 1   | `0x6B`  |

The STeaMi board uses **0x6B** (default).

---

# Basic Usage

```python
from machine import I2C
from ism330dl import ISM330DL

i2c = I2C(1)

imu = ISM330DL(i2c)

ax, ay, az = imu.acceleration_g()
gx, gy, gz = imu.gyroscope_dps()
temp = imu.temperature_c()

print("Accel:", ax, ay, az)
print("Gyro :", gx, gy, gz)
print("Temp :", temp)
```

---

# API

## Initialization

```python
imu = ISM330DL(i2c)
```

---

## Accelerometer

### Raw data

```python
imu.acceleration_raw()
```

Returns:

```
(x, y, z)
```

16-bit raw values.

---

### Acceleration in g

```python
imu.acceleration_g()
```

Example:

```
(0.01, -0.02, 0.99)
```

---

### Acceleration in m/s²

```python
imu.acceleration_ms2()
```

### Board orientation

```python
imu.orientation()
```

---

## Gyroscope

### Raw data

```python
imu.gyroscope_raw()
```

---

### Angular velocity in degrees per second

```python
imu.gyroscope_dps()
```

Example:

```
(0.5, -0.3, 1.2)
```

---

### Angular velocity in radians per second

```python
imu.gyroscope_rads()
```

### Motion detection

```python
imu.motion()
```

---

## Temperature

```python
imu.temperature_c()
```

Example:

```
26.3
```

---

## Configuration

### Accelerometer

```python
imu.configure_accel(odr, scale)
```

Example:

```python
from ism330dl.const import ACCEL_ODR_104HZ, ACCEL_FS_4G

imu.configure_accel(ACCEL_ODR_104HZ, ACCEL_FS_4G)
```

---

### Gyroscope

```python
imu.configure_gyro(odr, scale)
```

Example:

```python
from ism330dl.const import GYRO_ODR_104HZ, GYRO_FS_500DPS

imu.configure_gyro(GYRO_ODR_104HZ, GYRO_FS_500DPS)
```

---

## Status

```python
imu.status()
```

Returns:

```
{
    "temp_ready": True,
    "gyro_ready": True,
    "accel_ready": True
}
```

---

## Power Down

```python
imu.power_down()
```

Stops accelerometer and gyroscope.

---

# Examples

The repository provides several example scripts:

| Example                 | Description                                       |
| ----------------------- | ------------------------------------------------- |
| `basic_read.py`         | Simple sensor readout                             |
| `static_orientation.py` | Detect device orientation using the accelerometer |
| `motion_orientation.py` | Detect rotation using the gyroscope               |

---