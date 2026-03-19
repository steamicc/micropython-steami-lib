# STeaMi Config

Persistent configuration module for the STeaMi board.

Configuration data (board info, sensor calibration) is stored as compact JSON
in the STM32F103 internal flash config zone (1 KB) and survives firmware
updates and `clear_flash` operations.

---

# Dependencies

* `daplink_flash` — low-level config zone access

---

# Basic Usage

```python
from machine import I2C
from daplink_flash import DaplinkFlash
from steami_config import SteamiConfig

i2c = I2C(1)
config = SteamiConfig(DaplinkFlash(i2c))
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

# JSON Format

Data is stored as compact JSON to fit within 1 KB:

```json
{"rev":3,"name":"STeaMi-01","tc":{"hts":{"g":1.0,"o":-0.5},"pad":{"g":1.0,"o":-1.73}}}
```

| Key | Content |
| --- | ------- |
| `rev` | Board revision (int) |
| `name` | Board name (str) |
| `tc` | Temperature calibration dict |
| `tc.<key>.g` | Gain factor |
| `tc.<key>.o` | Offset in °C |

Sensor short keys: `hts` (HTS221), `mag` (LIS2MDL), `ism` (ISM330DL),
`hid` (WSEN-HIDS), `pad` (WSEN-PADS).

---

# Examples

| Example | Description |
| ------- | ----------- |
| `show_config.py` | Display current board configuration |
| `calibrate_temperature.py` | Calibrate all sensors against WSEN-HIDS reference |

Run with mpremote:

```sh
mpremote mount lib exec "
import sys
sys.path.insert(0, '/remote/steami_config')
sys.path.insert(0, '/remote/daplink_flash')
exec(open('/remote/steami_config/examples/show_config.py').read())
"
```

---

# Memory Note

Loading all five sensor drivers simultaneously exceeds the STM32WB55 RAM.
Use `gc.collect()` between sensor imports (see `calibrate_temperature.py`).
See issue #175 for investigation.
