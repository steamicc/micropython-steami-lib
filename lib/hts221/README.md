# HTS221 MicroPython Driver

MicroPython driver for the **STMicroelectronics HTS221** humidity and temperature sensor.

This library is a port of [MicroPython_HTS221](https://github.com/jposada202020/MicroPython_HTS221).

## Supported Sensor

| Parameter            | Value             |
| -------------------- | ----------------- |
| Interface            | I²C               |
| Default I²C address  | `0x5F`            |
| Device ID            | `0xBC`            |
| Humidity range       | 0–100 %RH         |
| Humidity accuracy    | ±3.5 %RH          |
| Temperature range    | −40 to +120 °C    |
| Temperature accuracy | ±0.5 °C           |

## Features

* I²C communication
* Device identification (`WHO_AM_I`)
* Humidity and temperature measurement
* One-shot and continuous measurement modes
* Configurable output data rate (ODR)
* Configurable averaging
* Data-ready status flags
* Power management (on/off, reboot)
* Factory calibration (automatic)
* User temperature calibration (offset and two-point)

## Basic Usage

```python
from machine import I2C
from hts221 import HTS221

i2c = I2C(1)
sensor = HTS221(i2c)

humidity = sensor.humidity()
temperature = sensor.temperature()

print("Humidity:", humidity, "%")
print("Temperature:", temperature, "°C")

# Read both at once
h, t = sensor.read()
```

## API Reference

### Initialization

```python
sensor = HTS221(i2c, address=0x5F)
```

### Device Information

```python
sensor.device_id()
```

Returns the sensor device ID (`WHO_AM_I` register, expected `0xBC`).

### Measurements

* `sensor.temperature()` — temperature in °C
* `sensor.humidity()` — relative humidity in %
* `sensor.read()` — returns `(humidity, temperature)`
* `sensor.read_one_shot()` — triggers a one-shot conversion and returns `(humidity, temperature)` after a fixed 15 ms delay

### Data Readiness

* `sensor.data_ready()` — `True` when both humidity and temperature are available
* `sensor.temperature_ready()` — `True` when temperature is available
* `sensor.humidity_ready()` — `True` when humidity is available

### One-Shot Mode

```python
sensor.trigger_one_shot()
```

Triggers a single conversion with a 15 ms delay. Used internally by `read_one_shot()`.

### Configuration

* `sensor.get_odr()` — returns current output data rate
* `sensor.set_odr(odr)` — set ODR (0 = one-shot, 1 = 1 Hz, 2 = 7 Hz, 3 = 12.5 Hz)
* `sensor.set_continuous(odr)` — enable continuous mode. Raises `ValueError` if `odr=0`.

### Averaging

* `sensor.get_av()` — returns current averaging configuration register
* `sensor.set_av(av)` — set humidity and temperature averaging (raw register value)

The AV_CONF register controls internal averaging for both channels. Higher values improve noise but increase conversion time. Refer to the HTS221 datasheet for the register encoding.

### Power Management

* `sensor.power_on()` — enable sensor
* `sensor.power_off()` — disable sensor
* `sensor.reboot()` — reload factory calibration data from non-volatile memory

### Temperature Calibration

```python
# Simple offset correction
sensor.set_temp_offset(-1.2)

# Two-point calibration (gain + offset)
sensor.calibrate_temperature(
    ref_low=0.0,
    measured_low=0.8,
    ref_high=50.0,
    measured_high=48.7,
)
```

No calibration is required for basic usage — the driver applies factory calibration automatically.

## Examples

| File          | Description                            |
| ------------- | -------------------------------------- |
| `humidity.py` | Basic humidity and temperature reading |

```bash
mpremote mount lib/hts221 run lib/hts221/examples/humidity.py
```

## Notes

* The driver uses factory calibration data stored in the sensor, read automatically at initialization.
* `temperature()`, `humidity()`, and `read()` poll the sensor's status bits via `_ensure_data()` to wait for fresh data before returning.
* `read_one_shot()` triggers a conversion and waits a fixed 15 ms delay before reading registers (no status polling).
* In power-down or one-shot mode, calling a measurement method automatically triggers a new conversion.
