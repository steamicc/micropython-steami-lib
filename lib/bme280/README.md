# BME280 MicroPython Driver

MicroPython driver for the **Bosch BME280** combined pressure, humidity, and temperature sensor.

This driver provides a simple API to read **pressure**, **humidity**, and **temperature** over **I2C**.

The BME280 is a high-precision environmental sensor suitable for applications such as:

* weather monitoring
* indoor air quality
* altimetry support
* environmental sensing

---

## Features

* I2C communication
* device identification
* pressure measurement (hPa)
* temperature measurement (C)
* relative humidity measurement (%RH)
* one-shot acquisition (forced mode)
* continuous measurement mode (normal mode)
* configurable oversampling (temperature, pressure, humidity)
* configurable IIR filter
* configurable standby time
* data-ready status helpers
* sleep mode (power off)
* soft reset and full reset with recalibration

---

## Sensor Overview

| Feature                | Value                   |
| ---------------------- | ----------------------- |
| Pressure range         | 300 hPa - 1100 hPa     |
| Pressure resolution    | 0.18 Pa (20-bit ADC)   |
| Temperature range      | -40 C to +85 C         |
| Temperature resolution | 0.01 C                 |
| Humidity range         | 0 - 100 %RH            |
| Humidity resolution    | 0.008 %RH (16-bit ADC) |
| Interface              | I2C / SPI              |
| Chip ID                | 0x60                    |

---

## I2C Address

The sensor can use two I2C addresses depending on the **SDO pin**:

| SDO    | Address |
| ------ | ------- |
| GND    | `0x76`  |
| VDDIO  | `0x77`  |

The default address used by the driver is **0x76**.

---

## Basic Usage

```python
from machine import I2C
from time import sleep
from bme280 import BME280

i2c = I2C(1)

sensor = BME280(i2c)

while True:
    temperature, pressure, humidity = sensor.read_one_shot()

    print("T:", temperature, "C")
    print("P:", pressure, "hPa")
    print("H:", humidity, "%RH")
    print()

    sleep(1)
```

---

## API Reference

## Initialization

```python
sensor = BME280(i2c)
```

Optional custom address:

```python
sensor = BME280(i2c, address=0x77)
```

The constructor verifies the chip ID, waits for NVM calibration data to be ready, reads factory trimming parameters, and applies a default configuration (1x oversampling, sleep mode).

---

## Measurements

### Read all channels

```python
temperature, pressure, humidity = sensor.read()
```

Returns a tuple of `(temperature_c, pressure_hpa, humidity_rh)`.

---

### Temperature

```python
sensor.temperature()
```

Returns the temperature in **degrees Celsius**.

---

### Pressure

```python
sensor.pressure_hpa()
```

Returns the pressure in **hPa**.

---

### Humidity

```python
sensor.humidity()
```

Returns the relative humidity in **%RH**.

---

### One-shot measurement

```python
temperature, pressure, humidity = sensor.read_one_shot()
```

Triggers a forced measurement, waits for completion, and returns all three channels.

---

### Trigger forced measurement

```python
sensor.trigger_one_shot()
```

Triggers a single forced measurement. Poll `data_ready()` for completion, then read values with `temperature()`, `pressure_hpa()`, `humidity()`, or `read()`.

---

## Data-Ready Status

```python
sensor.data_ready()          # True when all channels are ready
sensor.temperature_ready()   # True when temperature is ready
sensor.pressure_ready()      # True when pressure is ready
sensor.humidity_ready()      # True when humidity is ready
```

---

## Configuration

### Oversampling

```python
from bme280.const import OSRS_X2, OSRS_X4, OSRS_X16

sensor.set_oversampling(temperature=OSRS_X2, pressure=OSRS_X16, humidity=OSRS_X4)
```

Available constants: `OSRS_SKIP`, `OSRS_X1`, `OSRS_X2`, `OSRS_X4`, `OSRS_X8`, `OSRS_X16`.

Pass `None` to keep the current setting for a channel.

---

### IIR Filter

```python
from bme280.const import FILTER_4

sensor.set_iir_filter(FILTER_4)
```

Available constants: `FILTER_OFF`, `FILTER_2`, `FILTER_4`, `FILTER_8`, `FILTER_16`.

---

### Standby Time

```python
from bme280.const import STANDBY_500_MS

sensor.set_standby(STANDBY_500_MS)
```

Available constants: `STANDBY_0_5_MS`, `STANDBY_62_5_MS`, `STANDBY_125_MS`, `STANDBY_250_MS`, `STANDBY_500_MS`, `STANDBY_1000_MS`.

---

## Modes

### Sleep mode

```python
sensor.power_off()   # enter sleep mode, stop measurements
sensor.power_on()    # enter normal mode, continuous measurements
```

---

### Continuous mode

```python
from bme280.const import STANDBY_125_MS

sensor.set_continuous(standby=STANDBY_125_MS)
```

Enters normal mode with the specified standby time between measurements. If `standby` is `None`, the current standby setting is kept.

---

## Device Management

### Device ID

```python
sensor.device_id()   # returns 0x60
```

---

### Soft Reset

```python
sensor.soft_reset()
```

Sends the reset command and waits for NVM reload.

---

### Full Reset

```python
sensor.reset()
```

Performs a soft reset, re-reads calibration data, and re-applies default configuration.

---

## Examples

| Example              | Description                                        |
| -------------------- | -------------------------------------------------- |
| `basic_reader.py`    | Read temperature, pressure, and humidity            |
| `weather_station.py` | Continuous logging with altitude computation        |

---

## Comparison with other MicroPython BME280 drivers

| Feature | **STeaMi** | **robert-hh** | **Adafruit** | **neliogodoi** | **Pimoroni** | **RandomNerd** |
|---|---|---|---|---|---|---|
| I2C | Yes | Yes | Yes | Yes | Yes | Yes |
| SPI | No | No | Yes | No | No | No |
| Sleep mode | Yes | Yes | Yes | No | No | No |
| Forced mode | Yes | Yes | Yes | Implicit | No | No |
| Normal mode | Yes | Yes | Yes | No | Fixed | No |
| Oversampling (per channel) | Yes | Yes | Yes | Yes | Fixed x16 | Constants only |
| IIR filter | Yes | No | Yes | Yes | Fixed x16 | No |
| Standby time | Yes | No | Yes | No | Fixed 500ms | No |
| Altitude | No | Yes | Yes | Yes | Yes | No |
| Sea-level pressure | No | Yes | Yes | Yes | Yes | No |
| Dew point | No | Yes | No | No | No | No |
| Soft reset | Yes | No | No | No | Yes | No |
| Full reset + recalibration | Yes | No | No | No | No | No |
| power_off / power_on | Yes | No | Via mode | No | No | No |
| data_ready | Yes | No | No | No | No | No |
| read_one_shot | Yes | No | No | No | No | No |
| set_continuous | Yes | No | Via mode | No | No | No |
| Integer compensation | Yes | Yes | No | No | No | Yes |
| Measurement time estimate | No | No | Yes | No | No | No |
| Multi-unit temperature | No | No | No | C/F/K | No | C only |
| BMP280 compatibility | No | No | No | No | Yes | No |
| Dedicated exceptions | Yes | No | No | No | No | No |
| Mock test suite | Yes (39) | No | No | No | No | No |
| Hardware test suite | Yes (6) | No | No | No | No | No |

Reference implementations:

* [robert-hh/BME280](https://github.com/robert-hh/BME280) — integer compensation, altitude, dew point
* [Adafruit CircuitPython BME280](https://github.com/adafruit/Adafruit_CircuitPython_BME280) — I2C + SPI, basic/advanced split
* [neliogodoi/MicroPython-BME280](https://github.com/neliogodoi/MicroPython-BME280) — configurable oversampling and IIR
* [Pimoroni envirobit](https://github.com/pimoroni/micropython-envirobit) — Micro:bit driver, BMP280 alias
* [RandomNerdTutorials](https://randomnerdtutorials.com/micropython-bme280-esp32-esp8266/) — ESP32/ESP8266 tutorial

---

## References

* [BME280 Datasheet](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme280-ds002.pdf)
