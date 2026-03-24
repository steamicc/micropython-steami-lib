# WSEN-PADS MicroPython Driver

MicroPython driver for the **Würth Elektronik WSEN-PADS** absolute pressure sensor.

This driver provides a simple API to read **pressure** and **temperature** over **I²C**.

The WSEN-PADS is a high-resolution digital pressure sensor with integrated temperature measurement, suitable for applications such as:

* weather monitoring
* barometric measurements
* altimetry support
* environmental sensing

---

# Features

* I²C communication
* device identification
* pressure measurement
* temperature measurement
* one-shot acquisition
* continuous measurement mode
* configurable output data rate (ODR)
* optional low-pass filter
* raw pressure and temperature access
* data-ready status helpers
* power-down mode
* soft reset and reboot
* temperature offset calibration
* two-point temperature calibration

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

# I²C Address

The sensor can use two I²C addresses depending on the **SAO pin**:

| SAO  | Address |
| ---- | ------- |
| LOW  | `0x5C`  |
| HIGH | `0x5D`  |

The default address used by the driver is **0x5D**.

---

# Basic Usage

```python
from machine import I2C
from time import sleep
from wsen_pads import WSEN_PADS

i2c = I2C(1)

sensor = WSEN_PADS(i2c)

while True:
    pressure, temperature = sensor.read()

    print("Pressure:", pressure, "hPa")
    print("Temperature:", temperature, "°C")
    print()

    sleep(1)
```

---

# API Reference

## Initialization

```python
sensor = WSEN_PADS(i2c)
```

Optional custom address:

```python
sensor = WSEN_PADS(i2c, address=0x5C)
```

---

## Measurements

### Read pressure and temperature together

`read()` triggers a one-shot conversion internally. In continuous mode, prefer using `pressure_hpa()` and `temperature()` to avoid interrupting measurements.

```python
sensor.read()
```

Returns:

```python
(pressure_hpa, temperature_c)
```

Example:

```python
pressure, temperature = sensor.read()
print(pressure, temperature)
```

---

### Pressure in hPa

```python
sensor.pressure_hpa()
```

Returns the pressure in **hPa**.

---

### Pressure in Pa

```python
sensor.pressure_pa()
```

Returns the pressure in **Pa**.

---

### Pressure in kPa

```python
sensor.pressure_kpa()
```

Returns the pressure in **kPa**.

---

### Temperature in °C

```python
sensor.temperature()
```

Returns the temperature in **degrees Celsius**.

---

## Raw Data

### Raw pressure

```python
sensor.pressure_raw()
```

Returns a signed 24-bit raw pressure value.

---

### Raw temperature

```python
sensor.temperature_raw()
```

Returns a signed 16-bit raw temperature value.

---

## One-shot Measurement

### Trigger one conversion

```python
sensor.trigger_one_shot()
```

Optional low-noise conversion:

```python
sensor.trigger_one_shot(low_noise=True)
```

---

### Read one-shot measurement

```python
sensor.read_one_shot()
```

Returns:

```python
(pressure_hpa, temperature_c)
```

---

## Continuous Mode and Configuration

### Enable continuous mode

```python
sensor.set_continuous(odr)
```

Example:

```python
from wsen_pads.const import ODR_10_HZ

sensor.set_continuous(odr=ODR_10_HZ)
```

Available ODR values:

```python
ODR_1_HZ
ODR_10_HZ
ODR_25_HZ
ODR_50_HZ
ODR_75_HZ
ODR_100_HZ
ODR_200_HZ
```

---

### Continuous mode with options

```python
sensor.set_continuous(
    odr=ODR_25_HZ,
    low_noise=False,
    low_pass=False,
    low_pass_strong=False,
)
```

Parameters:

* `odr`: one of the `ODR_*` constants
* `low_noise`: enables low-noise mode
* `low_pass`: enables the pressure low-pass filter
* `low_pass_strong`: selects stronger low-pass filtering

---

### Enable low-pass filter

```python
sensor.enable_low_pass()
```

Strong filtering:

```python
sensor.enable_low_pass(strong=True)
```

---

### Disable low-pass filter

```python
sensor.disable_low_pass()
```

---

## Status

### Check if pressure data is ready

```python
sensor.pressure_ready()
```

Returns `True` when new pressure data is available.

---

### Check if temperature data is ready

```python
sensor.temperature_ready()
```

Returns `True` when new temperature data is available.

---

### Check if both pressure and temperature are ready

```python
sensor.data_ready()
```

Returns `True` when both measurements are available.

---

## Identification

### Read device ID

```python
sensor.device_id()
```

Returns the value of the sensor `DEVICE_ID` register.

---

## Power and Reset

### Power down

```python
sensor.power_off()
```

Puts the sensor in power-down mode.

---

### Power on

```python
sensor.power_on()
```

By default, resumes continuous measurements at `ODR_1_HZ`.

Custom ODR:

```python
sensor.power_on(odr=ODR_10_HZ)
```

---

### Soft reset

```python
sensor.soft_reset()
```

Resets user registers and restores the driver default configuration.

---

### Reboot

```python
sensor.reboot()
```

Reloads internal trimming parameters and restores the driver default configuration.

---

# Calibration

The driver supports software temperature calibration.

## Temperature offset calibration

Use this method when the sensor temperature is consistently shifted by a fixed offset.

```python
sensor.set_temp_offset(offset_c)
```

Example:

```python
sensor.set_temp_offset(-1.2)
```

This applies a simple correction in °C while keeping the gain at `1.0`.

---

## Two-point temperature calibration

Use this method when you want to correct both offset and slope from two reference measurements.

```python
sensor.calibrate_temperature(ref_low, measured_low, ref_high, measured_high)
```

Parameters:

* `ref_low`: reference temperature at the low point in °C
* `measured_low`: sensor reading at the low point in °C
* `ref_high`: reference temperature at the high point in °C
* `measured_high`: sensor reading at the high point in °C

Example:

```python
sensor.calibrate_temperature(
    ref_low=0.0,
    measured_low=0.8,
    ref_high=50.0,
    measured_high=48.7,
)
```

This computes a corrected gain and offset so that the measured temperature better matches the reference values.

---

# Notes

* If the sensor is in power-down mode, raw and converted read helpers automatically trigger a one-shot conversion before reading.
* In continuous mode, `pressure_ready()`, `temperature_ready()`, and `data_ready()` can be used to know when fresh data is available.
* Low-noise mode is not available at `ODR_100_HZ` or `ODR_200_HZ`.

---

# Examples

Examples are available in the `examples` directory.

| Example                    | Description                                                                 |
| -------------------------- | --------------------------------------------------------------------------- |
| `basic_reader.py`          | Basic pressure and temperature read                                         |
| `continuous_reader.py`     | Continuous measurement example                                              |
| `one_shot_reader.py`       | One-shot measurement example                                                |
| `altitude.py`              | Altitude estimation from pressure                                           |
| `altitude_calibration.py`  | Calibrate sea-level pressure from known altitude and compute corrected altitude |
| `floor_detector.py`        | Detect floor changes based on altitude variations                           |
| `pressure_trend.py`        | Track pressure changes over time to detect trends                           |
| `temp_pressure_display.py` | Display formatted temperature and pressure with ASCII bar graphs            |
| `treshold_alert.py`        | Monitor pressure and trigger an alert when a threshold is crossed           |
| `weather_station.py`       | Monitor weather condition and register them in a CSV file on the board      |

---

# Driver Structure

```text
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

# Hardware Connection

| Pin     | Description |
|--------|------------|
| VDD    | Power supply |
| GND    | Ground |
| SDA    | I²C data |
| SCL    | I²C clock |
| SAO    | I²C address selection |
