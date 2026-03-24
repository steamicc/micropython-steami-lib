"""Display the current board configuration stored in the config zone."""

from daplink_flash import DaplinkFlash
from machine import I2C
from steami_config import SteamiConfig

i2c = I2C(1)
config = SteamiConfig(DaplinkFlash(i2c))
config.load()

print("=== STeaMi Configuration ===")
print()

rev = config.board_revision
name = config.board_name
print("Board revision:", rev if rev is not None else "(not set)")
print("Board name:    ", name if name is not None else "(not set)")

sensors = ["hts221", "lis2mdl", "ism330dl", "wsen_hids", "wsen_pads"]
print()
print("Temperature calibration:")
has_cal = False
for sensor in sensors:
    cal = config.get_temperature_calibration(sensor)
    if cal is not None:
        has_cal = True
        print("  {:10s}  gain={:.4f}  offset={:+.2f} C".format(
            sensor, cal["gain"], cal["offset"],
        ))
if not has_cal:
    print("  (none)")

print()
print("Raw JSON:", config._data)
