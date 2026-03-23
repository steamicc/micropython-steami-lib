# BQ27441 MicroPython Driver

MicroPython driver for the **Texas Instruments BQ27441-G1A** LiPo fuel gauge.

This library is a port of the [SparkFun BQ27441 Arduino Library](https://github.com/sparkfun/SparkFun_BQ27441_Arduino_Library).

## Supported Device

| Parameter            | Value            |
| -------------------- | ---------------- |
| Device               | BQ27441-G1A      |
| Interface            | I²C              |
| Default I²C address  | `0x55`           |
| Operating voltage    | 2.5–4.5 V       |
| Default capacity     | 650 mAh          |

**Note:** The BQ27441 only responds on I²C when a battery is connected.

## Features

* Battery voltage measurement (mV)
* State of charge (%)
* Remaining and full capacity (mAh)
* Average, standby, and max current
* Average power
* State of health (%)
* Battery and internal temperature
* Configurable design capacity
* Power management (shutdown / wake-up)
* GPOUT interrupt configuration (SOC_INT / BAT_LOW)
* Seal / unseal device control

## Basic Usage

```python
from machine import I2C
from bq27441 import BQ27441

i2c = I2C(1)
bq = BQ27441(i2c)

print("Voltage:", bq.voltage_mv(), "mV")
print("Charge:", bq.state_of_charge(), "%")
print("Current:", bq.current_average(), "mA")
```

## API Reference

### Initialization

```python
bq = BQ27441(i2c, address=0x55)
```

### Quick Measurements

* `bq.voltage_mv()` — battery voltage in mV
* `bq.state_of_charge()` — battery level in % (filtered)
* `bq.capacity_remaining()` — remaining capacity in mAh
* `bq.capacity_full()` — full charge capacity in mAh
* `bq.current_average()` — average current in mA
* `bq.state_of_health()` — battery health in %
* `bq.power()` — average power in mW

### Advanced Measurements with Type Constants

Several methods accept a type parameter for different measurement modes. The type constants are defined in `bq27441.device`:

```python
from bq27441.device import CurrentMeasureType, CapacityMeasureType
from bq27441.device import SocMeasureType, SohMeasureType, TempMeasureType
```

#### Current

```python
bq.current(CurrentMeasureType.AVG)    # Average current (default)
bq.current(CurrentMeasureType.STBY)   # Standby current
bq.current(CurrentMeasureType.MAX)    # Max current
```

#### Capacity

```python
bq.capacity(CapacityMeasureType.REMAIN)      # Remaining (default)
bq.capacity(CapacityMeasureType.FULL)         # Full charge
bq.capacity(CapacityMeasureType.AVAIL)        # Available
bq.capacity(CapacityMeasureType.AVAIL_FULL)   # Full available
bq.capacity(CapacityMeasureType.REMAIN_F)     # Remaining filtered
bq.capacity(CapacityMeasureType.REMAIN_UF)    # Remaining unfiltered
bq.capacity(CapacityMeasureType.FULL_F)       # Full filtered
bq.capacity(CapacityMeasureType.FULL_UF)      # Full unfiltered
bq.capacity(CapacityMeasureType.DESIGN)       # Design capacity
```

#### State of Charge

```python
bq.soc(SocMeasureType.FILTERED)     # Filtered SoC (default)
bq.soc(SocMeasureType.UNFILTERED)   # Unfiltered SoC
```

#### State of Health

```python
bq.soh(SohMeasureType.PERCENT)    # Health percentage (default)
bq.soh(SohMeasureType.SOH_STAT)   # Health status bits
```

#### Temperature

```python
bq.temperature(TempMeasureType.BATTERY)        # Battery temperature
bq.temperature(TempMeasureType.INTERNAL_TEMP)  # Internal IC temperature
```

**Note:** Temperature is returned as a raw register value (units of 0.1 K). To convert to °C: `temp_c = raw / 10.0 - 273.15`.

### Configuration

```python
# Set battery design capacity
bq.set_capacity(650)

# Configuration mode (required for some settings)
bq.enter_config(user_control=True)
# ... modify settings ...
bq.exit_config(resim=True)
```

### GPOUT / Alerts

```python
from bq27441.device import GpoutFunctionType

# Configure GPOUT function
bq.set_gpout_function(GpoutFunctionType.SOC_INT)  # SoC change interrupt
bq.set_gpout_function(GpoutFunctionType.BAT_LOW)   # Battery low alert

# GPOUT polarity
bq.gpout_polarity()                  # Read current polarity
bq.set_gpout_polarity(active_high=True)

# GPOUT pin direction
bq.configure_gpout_input()
bq.configure_gpout_output()

# SoC thresholds
bq.set_soc1_thresholds(set_soc=15, clear_soc=20)
bq.set_socf_thresholds(set_socf=5, clear_socf=10)

# Read thresholds
bq.soc1_set_threshold()
bq.soc1_clear_threshold()
bq.socf_set_threshold()
bq.socf_clear_threshold()

# SoC flags and delta
bq.soc_flag()                        # SoC1 threshold crossed
bq.socf_flag()                       # SoCF threshold crossed
bq.soci_delta()                      # SoC interrupt delta
bq.set_soci_delta(delta=1)

# Pulse GPOUT
bq.pulse_gpout()
```

### Power Management

* `bq.power_on()` — wake device from shutdown
* `bq.power_off()` — enter shutdown mode
* `bq.enable_shutdown_mode()` — enable shutdown via GPOUT
* `bq.enter_shutdown_mode()` — enter shutdown
* `bq.disable_shutdown_mode()` — disable shutdown mode

### Device Control

* `bq.device_id()` — read device type ID
* `bq.is_valid_device()` — check if device is BQ27441
* `bq.flags()` — read status flags register
* `bq.reset()` — full device reset
* `bq.soft_reset()` — soft reset

### Seal / Unseal

* `bq.sealed()` — check if device is sealed
* `bq.seal()` — seal the device (restrict configuration access)
* `bq.unseal()` — unseal for configuration

### Operation Config

* `bq.op_config()` — read OpConfig register
* `bq.write_op_config(value)` — write OpConfig register

## Examples

| File             | Description                                      |
| ---------------- | ------------------------------------------------ |
| `fuel_gauge.py`  | Battery monitoring (voltage, SoC, current, health) |

```bash
mpremote mount lib/bq27441 run lib/bq27441/examples/fuel_gauge.py
```

## Notes

* The BQ27441 requires a connected LiPo battery to respond on I²C.
* Default design capacity is 650 mAh (configurable via `set_capacity()`).
* Some configuration operations require entering config mode with `enter_config()`.
* The device may be sealed; use `unseal()` before advanced configuration.
* Temperature readings are raw register values in 0.1 K units (see conversion above).
