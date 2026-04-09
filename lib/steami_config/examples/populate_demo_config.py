"""Populate the config zone with demo values for testing.

WARNING: This overwrites all persistent configuration data
(board info, calibrations, boot counter) with fictitious values.
Only use for testing or demonstration purposes.
"""

from daplink_bridge import DaplinkBridge
from machine import I2C
from steami_config import SteamiConfig

i2c = I2C(1)
bridge = DaplinkBridge(i2c)
config = SteamiConfig(bridge)

# Board info
config.board_revision = 3
config.board_name = "STeaMi Demo Board"

# Temperature calibration (example values)
config.set_temperature_calibration("hts221", gain=1.01, offset=-0.5)
config.set_temperature_calibration("lis2mdl", gain=0.99, offset=+0.2)
config.set_temperature_calibration("ism330dl", gain=1.00, offset=0.0)
config.set_temperature_calibration("wsen_hids", gain=1.02, offset=-0.3)
config.set_temperature_calibration("wsen_pads", gain=0.98, offset=+0.4)

# Magnetometer calibration
config.set_magnetometer_calibration(
    hard_iron_x=+10.5,
    hard_iron_y=-3.2,
    hard_iron_z=+1.7,
    soft_iron_x=1.02,
    soft_iron_y=0.97,
    soft_iron_z=1.05,
)

# Accelerometer calibration
config.set_accelerometer_calibration(
    ox=+0.01,
    oy=-0.02,
    oz=+0.03,
)

# Boot counter
config.set_boot_count(42)

# Save everything
config.save()

print("Demo config written. Run show_config.py to verify.")
