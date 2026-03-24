"""Calibrate all temperature sensors against WSEN-HIDS reference.

This example reads each sensor one at a time to stay within RAM
limits on the STM32WB55.  Calibration offsets are stored in the
persistent config zone and survive power cycles.
"""

import gc
import sys
from time import sleep_ms

from daplink_flash.device import DaplinkFlash
from machine import I2C
from steami_config.device import SteamiConfig
from wsen_hids.device import WSEN_HIDS

i2c = I2C(1)
flash = DaplinkFlash(i2c)
config = SteamiConfig(flash)
config.load()

# Read reference temperature from WSEN-HIDS (most accurate at ambient)
ref_temp = WSEN_HIDS(i2c).temperature()
print("Reference (WSEN-HIDS): {:.2f} C".format(ref_temp))
config.set_temperature_calibration("wsen_hids", gain=1.0, offset=0.0)
del WSEN_HIDS
sys.modules.pop("wsen_hids.device", None)
gc.collect()

# Calibrate each sensor one at a time to save RAM
SENSORS = [
    ("hts221", "hts221.device", "HTS221", "temperature"),
    ("wsen_pads", "wsen_pads.device", "WSEN_PADS", "temperature"),
    ("lis2mdl", "lis2mdl.device", "LIS2MDL", "temperature"),
    ("ism330dl", "ism330dl.device", "ISM330DL", "temperature"),
]

for config_name, module, class_name, method in SENSORS:
    mod = __import__(module, None, None, [class_name])
    cls = getattr(mod, class_name)
    sensor = cls(i2c)
    if config_name == "ism330dl":
        sleep_ms(200)
    raw = getattr(sensor, method)()
    offset = ref_temp - raw
    config.set_temperature_calibration(config_name, gain=1.0, offset=offset)
    print("  {:10s}: {:6.2f} C -> offset {:+.2f}".format(config_name, raw, offset))
    del sensor, cls, mod
    sys.modules.pop(module, None)
    gc.collect()

config.save()
print("\nCalibration saved.")

# Verify by reloading
gc.collect()
config2 = SteamiConfig(flash)
config2.load()

print("\nVerification (after reload):")
for config_name, module, class_name, method in SENSORS:
    mod = __import__(module, None, None, [class_name])
    cls = getattr(mod, class_name)
    sensor = cls(i2c)
    if config_name == "ism330dl":
        sleep_ms(200)
    config2.apply_temperature_calibration(sensor)
    print("  {:10s}: {:6.2f} C".format(config_name, getattr(sensor, method)()))
    del sensor, cls, mod
    sys.modules.pop(module, None)
    gc.collect()
