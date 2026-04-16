# APDS-9960 MicroPython Driver

MicroPython driver for the **Broadcom APDS-9960** proximity, gesture, color, and ambient light sensor.

This library is a port of [python-apds9960](https://github.com/liske/python-apds9960/).

## Supported Sensor

| Parameter           | Value                             |
| ------------------- | --------------------------------- |
| Device              | APDS-9960                         |
| Interface           | I²C                               |
| Default I²C address | `0x39`                            |
| Device ID           | `0xAB`                            |
| Functions           | ALS, RGB, proximity, gesture      |
| Proximity range     | 0–255 (relative)                  |
| ALS resolution      | 16-bit per channel                |

## Features

* Ambient light sensing (ALS) — clear channel
* RGB color sensing — red, green, blue channels
* Proximity detection — object distance estimation
* Gesture detection — directional gestures (up, down, left, right, near, far)
* Power management (on/off)
* Configurable gains, LED drive, and thresholds
* Interrupt support for light, proximity, and gesture

## Basic Usage

```python
from machine import I2C
from apds9960 import uAPDS9960

i2c = I2C(1)
sensor = uAPDS9960(i2c)

# Read ambient light
ambient = sensor.ambient_light()
print("Ambient light:", ambient)

# Read proximity
prox = sensor.proximity()
print("Proximity:", prox)
```

## API Reference

### General

* `sensor.device_id()` — read device ID (expected `0xAB`)
* `sensor.power_on()` — enable the sensor
* `sensor.power_off()` — disable the sensor
* `sensor.data_ready()` — `True` when light and proximity data are ready
* `sensor.get_mode()` — read current mode register
* `sensor.set_mode(mode, enable=True)` — enable or disable a sensor mode

### Ambient Light and Color

#### Measurements

* `sensor.ambient_light()` — read ambient (clear) light value
* `sensor.red_light()` — read red channel
* `sensor.green_light()` — read green channel
* `sensor.blue_light()` — read blue channel
* `sensor.light_ready()` — `True` when light data is available

#### Control

* `sensor.enable_light_sensor(interrupts=True)` — enable ALS
* `sensor.disable_light_sensor()` — disable ALS

#### Configuration

* `sensor.get_ambient_light_gain()` / `sensor.set_ambient_light_gain(value)` — ALS gain (0=1x, 1=4x, 2=16x, 3=64x)
* `sensor.get_light_int_low_threshold()` / `sensor.set_light_int_low_threshold(value)` — low interrupt threshold
* `sensor.get_light_int_high_threshold()` / `sensor.set_light_int_high_threshold(value)` — high interrupt threshold
* `sensor.get_ambient_light_int_enable()` / `sensor.set_ambient_light_int_enable(enable)` — interrupt enable
* `sensor.clear_ambient_light_int()` — clear light interrupt

### Proximity

#### Measurements

* `sensor.proximity()` — read proximity value (0–255)
* `sensor.proximity_ready()` — `True` when proximity data is available

#### Control

* `sensor.enable_proximity_sensor(interrupts=True)` — enable proximity
* `sensor.disable_proximity_sensor()` — disable proximity

#### Configuration

* `sensor.get_proximity_gain()` / `sensor.set_proximity_gain(gain)` — proximity gain (0=1x, 1=2x, 2=4x, 3=8x)
* `sensor.get_led_drive()` / `sensor.set_led_drive(drive)` — LED drive strength (0=100mA, 1=50mA, 2=25mA, 3=12.5mA)
* `sensor.get_led_boost()` / `sensor.set_led_boost(boost)` — LED boost
* `sensor.get_prox_int_low_thresh()` / `sensor.set_prox_int_low_thresh(value)` — low proximity threshold
* `sensor.get_prox_int_high_thresh()` / `sensor.set_prox_int_high_thresh(value)` — high proximity threshold
* `sensor.get_proximity_int_low_threshold()` / `sensor.set_proximity_int_low_threshold(value)` — low threshold (alternative)
* `sensor.get_proximity_int_high_threshold()` / `sensor.set_proximity_int_high_threshold(value)` — high threshold (alternative)
* `sensor.get_proximity_int_enable()` / `sensor.set_proximity_int_enable(enable)` — interrupt enable
* `sensor.clear_proximity_int()` — clear proximity interrupt
* `sensor.get_prox_photo_mask()` / `sensor.set_prox_photo_mask(mask)` — photodiode mask
* `sensor.get_prox_gain_comp_enable()` / `sensor.set_prox_gain_comp_enable(enable)` — gain compensation

### Gesture

#### Measurements

```python
sensor.enable_gesture_sensor()

if sensor.is_gesture_available():
    gesture = sensor.gesture()
```

* `sensor.gesture()` — read detected gesture
* `sensor.is_gesture_available()` — `True` when a gesture is pending

**Note:** Gesture detection is not auto-enabled. Call `enable_gesture_sensor()` before polling `gesture()`.

#### Control

* `sensor.enable_gesture_sensor(interrupts=True)` — enable gesture detection
* `sensor.disable_gesture_sensor()` — disable gesture detection

#### Configuration

* `sensor.get_gesture_enter_thresh()` / `sensor.set_gesture_enter_thresh(value)` — entry threshold
* `sensor.get_gesture_exit_thresh()` / `sensor.set_gesture_exit_thresh(value)` — exit threshold
* `sensor.get_gesture_gain()` / `sensor.set_gesture_gain(value)` — gesture gain
* `sensor.get_gesture_led_drive()` / `sensor.set_gesture_led_drive(value)` — gesture LED drive
* `sensor.get_gesture_wait_time()` / `sensor.set_gesture_wait_time(value)` — wait time between gesture cycles
* `sensor.get_gesture_int_enable()` / `sensor.set_gesture_int_enable(enable)` — gesture interrupt enable
* `sensor.get_gesture_mode()` / `sensor.set_gesture_mode(enable)` — gesture mode

#### Advanced

* `sensor.reset_gesture_parameters()` — reset internal gesture state
* `sensor.process_gesture_data()` — process raw gesture FIFO data
* `sensor.decode_gesture()` — decode gesture direction from processed data

### Exceptions

* `APDS9960InvalidDevId` — raised when device ID does not match `0xAB`
* `APDS9960InvalidMode` — raised for invalid mode selection

## Examples

| File               | Description                      |
| ------------------ | -------------------------------- |
| `ambient_light.py` | Read ambient light and RGB values |
| `proximity.py`     | Detect nearby objects             |
| `gesture.py`       | Detect directional gestures       |
| `color_lamp.py`         | Reactive color lamp with auto-calibration and OLED display. **Dependency: `ssd1327`** |

```bash
mpremote mount lib/apds9960 run lib/apds9960/examples/ambient_light.py
```

## Notes

* Ambient light and proximity reads automatically enable their respective sensors when needed (lazy activation).
* Gesture detection must be explicitly enabled before polling.
* Both `APDS9960` and `uAPDS9960` (MicroPython-optimized) classes are exported.
