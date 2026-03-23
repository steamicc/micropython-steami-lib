# MicroPython BQ27441 Library

This library is a port of the [SparkFun BQ27441-G1A LiPo Fuel Gauge Arduino Library](https://github.com/sparkfun/SparkFun_BQ27441_Arduino_Library). 

# Features

* I²C communication
* battery voltage measurement
* state of charge (SoC)
* remaining and full capacity
* average, standby and max current
* average power measurement
* state of health (SoH)
* battery and internal temperature
* configurable design capacity
* power management (shutdown / wake-up)
* GPOUT interrupt configuration (SOC_INT / BAT_LOW)

# I2C Address

* **Default address:** `0x55` 

**Important:**
The BQ27441 only responds on I²C when a **battery is connected**.

# Basic Usage

```python
from machine import I2C
from bq27441 import BQ27441

i2c = I2C(1)

bq = BQ27441(i2c)

voltage = bq.voltage_mv()        # mV
soc = bq.state_of_charge()       # %

print("Voltage:", voltage, "mV")
print("State of Charge:", soc, "%")
```

# API

## Measurements

### Voltage & Power

* `voltage_mv()` — battery voltage in mV
* `power()` — average power

### Current

* `current_average()` — average current
* `current(type)` — current (AVG, STBY, MAX)

### Capacity

* `capacity_remaining()` — remaining capacity (mAh)
* `capacity_full()` — full charge capacity (mAh)
* `capacity(type)` — advanced capacity readings

### Charge & Health

* `state_of_charge()` — battery level (%)
* `soc(type)` — filtered / unfiltered SoC
* `state_of_health()` — battery health (%)
* `soh(type)` — detailed SoH

### Temperature

* `temperature(type)` — battery or internal temperature

## Configuration

* `set_capacity(mAh)` — set battery design capacity
* `enter_config(user_control)` — enter config mode
* `exit_config(resim=True)` — exit config mode

### GPOUT / Alerts

* `set_gpout_function(type)` — SOC_INT or BAT_LOW
* `set_gpout_polarity(active_high)`
* `set_soc1_thresholds(set, clear)`
* `set_socf_thresholds(set, clear)`
* `pulse_gpout()`

## Power Management

* `power_on()` — wake device
* `power_off()` — enter shutdown
* `enable_shutdown_mode()`
* `enter_shutdown_mode()`
* `disable_shutdown_mode()`

## Device Info & Control

* `device_id()` — read device ID
* `is_valid_device()` — check device identity
* `flags()` — read status flags
* `reset()` — full reset
* `soft_reset()` — soft reset

# Examples

| Example file    | Description                                      |
| --------------- | ------------------------------------------------ |
| `fuel_gauge.py` | Basic battery monitoring (voltage, SoC, current) |

Run with:

```sh
mpremote mount lib/bq27441 run lib/bq27441/examples/fuel_gauge.py
```

---

# Notes

* The **BQ27441 requires a connected LiPo battery** to respond on I²C
* Default design capacity is **650 mAh** (configurable) 
* Some configuration operations require entering **config mode**
* The device may be **sealed**, requiring unsealing for advanced configuration
