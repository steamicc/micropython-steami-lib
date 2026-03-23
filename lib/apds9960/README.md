# MicroPython APDS-9960 Library

This library is a port of the [Python (and MicroPython) APDS-9960 Library](https://github.com/liske/python-apds9960/).

## Features

The APDS-9960 is a multifunction sensor providing:

* **Ambient light sensing (ALS)** — clear + RGB channels
* **RGB color sensing** — red, green, blue intensity
* **Proximity detection** — object distance estimation
* **Gesture detection** — directional gestures (up, down, left, right, near, far)

## I2C Address

Default I2C address:

```python
0x39
```

## Basic Usage

```python
from machine import I2C, Pin
from apds9960 import uAPDS9960

i2c = I2C(0, scl=Pin(22), sda=Pin(21))
sensor = uAPDS9960(i2c)

# Read ambient light
ambient = sensor.ambient_light()
print("Ambient light:", ambient)
```

Parfait — voici une version **alignée sur le style ism330dl / wsen-hids**, avec wording homogène, phrases courtes et impératives, et structure cohérente.

---

## API

### General

* `device_id()`
  Get the device ID

* `power_on()`
  Enable the sensor

* `power_off()`
  Disable the sensor

* `get_mode()`
  Get the current mode register value

* `set_mode(mode, enable=True)`
  Enable or disable a sensor mode

* `data_ready()`
  Check if light and proximity data are ready

## API

### Ambient Light & Color

#### Reading measurements

```python
ambient = sensor.ambient_light()
red = sensor.red_light()
green = sensor.green_light()
blue = sensor.blue_light()
```

* `ambient_light()`
  Read ambient (clear) light value

* `red_light()`
  Read red channel value

* `green_light()`
  Read green channel value

* `blue_light()`
  Read blue channel value

* `light_ready()`
  Check if light data is ready

#### Sensor control

* `enable_light_sensor(interrupts=True)`
  Enable ambient light sensing

* `disable_light_sensor()`
  Disable ambient light sensing

#### Configuration

* `get_ambient_light_gain()` / `set_ambient_light_gain(value)`
  Get or set ambient light gain

* `get_light_int_low_threshold()` / `set_light_int_low_threshold(value)`
  Get or set low interrupt threshold

* `get_light_int_high_threshold()` / `set_light_int_high_threshold(value)`
  Get or set high interrupt threshold

* `get_ambient_light_int_enable()` / `set_ambient_light_int_enable(enable)`
  Enable or disable light interrupts

* `clear_ambient_light_int()`
  Clear ambient light interrupt

### Proximity

#### Reading measurements

```python
proximity = sensor.proximity()
```

* `proximity()`
  Read proximity value

* `proximity_ready()`
  Check if proximity data is ready

#### Sensor control

* `enable_proximity_sensor(interrupts=True)`
  Enable proximity sensing

* `disable_proximity_sensor()`
  Disable proximity sensing

#### Configuration

* `get_proximity_gain()` / `set_proximity_gain(value)`
  Get or set proximity gain

* `get_led_drive()` / `set_led_drive(value)`
  Get or set LED drive strength

* `get_led_boost()` / `set_led_boost(value)`
  Get or set LED boost

* `get_prox_int_low_thresh()` / `set_prox_int_low_thresh(value)`
  Get or set low proximity threshold

* `get_prox_int_high_thresh()` / `set_prox_int_high_thresh(value)`
  Get or set high proximity threshold

* `get_proximity_int_enable()` / `set_proximity_int_enable(enable)`
  Enable or disable proximity interrupts

* `clear_proximity_int()`
  Clear proximity interrupt

* `get_prox_photo_mask()` / `set_prox_photo_mask(mask)`
  Get or set proximity photodiode mask

* `get_prox_gain_comp_enable()` / `set_prox_gain_comp_enable(enable)`
  Enable or disable gain compensation

### Gesture

#### Reading measurements

```python
sensor.enable_gesture_sensor()

if sensor.is_gesture_available():
    gesture = sensor.gesture()
```

* `gesture()`
  Read detected gesture

* `is_gesture_available()`
  Check if a gesture is available

#### Sensor control

* `enable_gesture_sensor(interrupts=True)`
  Enable gesture detection

* `disable_gesture_sensor()`
  Disable gesture detection

#### Configuration

* `get_gesture_enter_thresh()` / `set_gesture_enter_thresh(value)`
  Get or set gesture entry threshold

* `get_gesture_exit_thresh()` / `set_gesture_exit_thresh(value)`
  Get or set gesture exit threshold

* `get_gesture_gain()` / `set_gesture_gain(value)`
  Get or set gesture gain

* `get_gesture_led_drive()` / `set_gesture_led_drive(value)`
  Get or set gesture LED drive

* `get_gesture_wait_time()` / `set_gesture_wait_time(value)`
  Get or set gesture wait time

* `get_gesture_int_enable()` / `set_gesture_int_enable(enable)`
  Enable or disable gesture interrupts

* `get_gesture_mode()` / `set_gesture_mode(enable)`
  Enable or disable gesture mode

#### Advanced

* `reset_gesture_parameters()`
  Reset internal gesture state

* `process_gesture_data()`
  Process raw gesture data

* `decode_gesture()`
  Decode gesture direction from data

## Sensor Control

### Enable sensors

```python
sensor.enable_light_sensor()
sensor.enable_proximity_sensor()
sensor.enable_gesture_sensor()
```

### Disable sensors

```python
sensor.disable_light_sensor()
sensor.disable_proximity_sensor()
sensor.disable_gesture_sensor()
```

## Configuration Examples

### Set ambient light gain

```python
sensor.set_ambient_light_gain(1)  # 1x, 4x, 16x, 64x
```

### Set proximity gain

```python
sensor.set_proximity_gain(2)  # 1x, 2x, 4x, 8x
```

### Set LED drive strength

```python
sensor.set_led_drive(0)  # 100mA, 50mA, 25mA, 12.5mA
```

### Exceptions

* `APDS9960InvalidDevId` — invalid device ID detected
* `APDS9960InvalidMode` — invalid mode selection 

## Examples

| Example                     | Description               |
| --------------------------- | ------------------------- |
| `examples/ambient_light.py` | Read ambient light values |
| `examples/proximity.py`     | Detect object proximity   |
| `examples/gesture.py`       | Detect gestures           |

Run example:

```sh
mpremote mount lib/apds9960 run lib/apds9960/examples/ambient_light.py
```

## Notes

* The driver automatically enables sensors when needed (lazy activation).
* Gesture detection requires continuous polling via `gesture()`.
* Works with both:

  * `APDS9960` (generic Python)
  * `uAPDS9960` (MicroPython optimized) 
