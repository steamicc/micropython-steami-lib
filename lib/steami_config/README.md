# STeaMi Config

Persistent configuration module for the STeaMi board.

Configuration data (board info, sensor calibration) is stored as compact JSON
in the STM32F103 internal flash config zone (1 KB) and survives firmware
updates and `clear_flash` operations.

---

# Dependencies

* `daplink_bridge` — low-level I2C bridge and config zone access

---

# Basic Usage

```python
from machine import I2C
from daplink_bridge import DaplinkBridge
from steami_config import SteamiConfig

i2c = I2C(1)
config = SteamiConfig(DaplinkBridge(i2c))
config.load()

print(config.board_name)
print(config.board_revision)
```

---

# API

## Persistence

```python
config.load()   # read config zone -> JSON -> internal dict
config.save()   # internal dict -> JSON -> config zone
```

---

## Board Info

```python
config.board_revision          # -> int or None
config.board_revision = 3

config.board_name              # -> str or None
config.board_name = "STeaMi-01"
```

---

## Temperature Calibration

Five sensors are supported: `hts221`, `lis2mdl`, `ism330dl`, `wsen_hids`,
`wsen_pads`.

### Store calibration

```python
config.set_temperature_calibration("hts221", gain=1.0, offset=-0.5)
```

### Read calibration

```python
cal = config.get_temperature_calibration("hts221")
# -> {"gain": 1.0, "offset": -0.5}   or   None
```

### Apply calibration to a sensor

```python
from hts221 import HTS221

hts = HTS221(i2c)
config.apply_temperature_calibration(hts)
# hts._temp_gain and hts._temp_offset are now set
```

The sensor class name is used for lookup (`HTS221` -> `"hts221"`).

---

## Magnetometer Calibration

Store and restore hard-iron and soft-iron calibration for the LIS2MDL.

### Store calibration

```python
config.set_magnetometer_calibration(
    hard_iron_x=12.3, hard_iron_y=-5.1, hard_iron_z=0.8,
    soft_iron_x=1.01, soft_iron_y=0.98, soft_iron_z=1.0,
)
```

### Read calibration

```python
cal = config.get_magnetometer_calibration()
# -> {"hard_iron_x": 12.3, ..., "soft_iron_z": 1.0}   or   None
```

### Apply calibration to a sensor

```python
from lis2mdl import LIS2MDL

mag = LIS2MDL(i2c)
config.apply_magnetometer_calibration(mag)
# mag.x_off, y_off, z_off, x_scale, y_scale, z_scale are now set
```

---

## Accelerometer Calibration

Store and restore accelerometer bias offsets for the ISM330DL.

### Store calibration

```python
config.set_accelerometer_calibration(ox=0.01, oy=-0.02, oz=0.03)
Read calibration
cal = config.get_accelerometer_calibration()
# -> {"ox": 0.01, "oy": -0.02, "oz": 0.03}   or   None
```

### Apply calibration to a sensor
```python
from ism330dl import ISM330DL

imu = ISM330DL(i2c)
config.apply_accelerometer_calibration(imu)
```

---

# JSON Format

Data is stored as compact JSON to fit within 1 KB:

```json
{"rev":3,"name":"STeaMi-01","tc":{"hts":{"g":1.0,"o":-0.5}},"cm":{"hx":12.3,"hy":-5.1,"hz":0.8,"sx":1.01,"sy":0.98,"sz":1.0},"cal_accel":{"ox":0.01,"oy":-0.02,"oz":0.03}}
```

| Key | Content |
| --- | ------- |
| `rev` | Board revision (int) |
| `name` | Board name (str) |
| `tc` | Temperature calibration dict |
| `tc.<key>.g` | Gain factor |
| `tc.<key>.o` | Offset in °C |
| `cm` | Magnetometer calibration dict |
| `cm.hx/hy/hz` | Hard-iron offsets (X, Y, Z) |
| `cm.sx/sy/sz` | Soft-iron scale factors (X, Y, Z) |
| `cal_accel` | Accelerometer calibration dict |
| `cal_accel.ox/oy/oz` | Bias offsets in g (X, Y, Z) |

Sensor short keys: `hts` (HTS221), `mag` (LIS2MDL), `ism` (ISM330DL),
`hid` (WSEN-HIDS), `pad` (WSEN-PADS).

---

# Examples

| Example | Description |
| ------- | ----------- |
| `show_config.py` | Display current board configuration |
| `calibrate_temperature.py` | Calibrate all sensors against WSEN-HIDS reference |
| `calibrate_magnetometer.py` | Calibrate LIS2MDL with OLED display and persistent storage |
| `calibrate_accelerometer.py` | Calibrate ISM330DL accelerometer bias and persist it |

Run with mpremote:

```sh
mpremote mount lib exec "
import sys
sys.path.insert(0, '/remote/steami_config')
sys.path.insert(0, '/remote/daplink_bridge')
exec(open('/remote/steami_config/examples/show_config.py').read())
"
```

---

# Memory Note

Loading all five sensor drivers simultaneously exceeds the STM32WB55 RAM.
Use `gc.collect()` between sensor imports (see `calibrate_temperature.py`).
See issue #175 for investigation.
