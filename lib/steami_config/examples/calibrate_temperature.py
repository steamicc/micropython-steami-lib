"""Calibrate all temperature sensors against WSEN-HIDS reference.

Reads the WSEN-HIDS sensor as reference, then computes an offset for
each other sensor.  Calibration offsets are stored in the persistent
config zone and survive power cycles.

Note: this example assumes the drivers are frozen into the firmware.
Use ``make firmware && make deploy`` to build a firmware with the
latest drivers before running this script.
"""

from time import sleep_ms

from daplink_bridge import DaplinkBridge
from hts221 import HTS221
from ism330dl import ISM330DL
from lis2mdl import LIS2MDL
from machine import I2C
from steami_config import SteamiConfig
from wsen_hids import WSEN_HIDS
from wsen_pads import WSEN_PADS

i2c = I2C(1)
bridge = DaplinkBridge(i2c)
config = SteamiConfig(bridge)
config.load()

# Read reference temperature from WSEN-HIDS (most accurate at ambient)
ref = WSEN_HIDS(i2c)
ref_temp = ref.temperature()
print("Reference (WSEN-HIDS): {:.2f} C".format(ref_temp))
config.set_temperature_calibration("wsen_hids", gain=1.0, offset=0.0)

# Calibrate each sensor
sensors = [
    ("hts221", HTS221(i2c)),
    ("wsen_pads", WSEN_PADS(i2c)),
    ("lis2mdl", LIS2MDL(i2c)),
    ("ism330dl", ISM330DL(i2c)),
]

for name, sensor in sensors:
    if name in ("ism330dl", "lis2mdl"):
        sleep_ms(200)
    raw = sensor.temperature()
    offset = ref_temp - raw
    config.set_temperature_calibration(name, gain=1.0, offset=offset)
    print("  {:10s}: {:6.2f} C -> offset {:+.2f}".format(name, raw, offset))

config.save()
print("\nCalibration saved.")

# Verify by reloading with fresh sensor instances (simulates a reboot)
config2 = SteamiConfig(bridge)
config2.load()

verify_sensors = [
    ("hts221", HTS221(i2c)),
    ("wsen_pads", WSEN_PADS(i2c)),
    ("lis2mdl", LIS2MDL(i2c)),
    ("ism330dl", ISM330DL(i2c)),
]

print("\nVerification (after reload):")
for name, sensor in verify_sensors:
    if name in ("ism330dl", "lis2mdl"):
        sleep_ms(200)
    config2.apply_temperature_calibration(sensor)
    print("  {:10s}: {:6.2f} C".format(name, sensor.temperature()))
