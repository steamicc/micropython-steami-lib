"""Calibrate the LIS2MDL magnetometer and save to persistent config.

This example runs a 3D min/max calibration by collecting samples while
the user rotates the board in all directions.  The computed hard-iron
offsets and soft-iron scale factors are stored in the config zone and
survive power cycles.

Usage:
    mpremote mount lib/ run lib/steami_config/examples/calibrate_magnetometer.py

When prompted, slowly rotate the board in all directions (tilt, roll,
yaw) for about 12 seconds.  The script then saves the calibration and
verifies it by displaying corrected heading readings.
"""

import gc
from time import sleep_ms

from daplink_flash.device import DaplinkFlash
from lis2mdl.device import LIS2MDL
from machine import I2C
from steami_config.device import SteamiConfig

i2c = I2C(1)
flash = DaplinkFlash(i2c)
config = SteamiConfig(flash)
config.load()

mag = LIS2MDL(i2c)

# Show current state
print("=== Magnetometer Calibration ===\n")
print("Current offsets:  x={:.1f}  y={:.1f}  z={:.1f}".format(
    mag.x_off, mag.y_off, mag.z_off))
print("Current scales:   x={:.3f}  y={:.3f}  z={:.3f}\n".format(
    mag.x_scale, mag.y_scale, mag.z_scale))

# Run 3D calibration
print("Rotate the board slowly in ALL directions for 12 seconds...")
print("(tilt, roll, turn upside down, spin...)\n")
sleep_ms(1000)

mag.calibrate_minmax_3d(samples=600, delay_ms=20)

print("Calibration complete!")
print("  Hard-iron offsets: x={:.1f}  y={:.1f}  z={:.1f}".format(
    mag.x_off, mag.y_off, mag.z_off))
print("  Soft-iron scales:  x={:.3f}  y={:.3f}  z={:.3f}\n".format(
    mag.x_scale, mag.y_scale, mag.z_scale))

# Save to config zone
config.set_magnetometer_calibration(
    hard_iron_x=mag.x_off,
    hard_iron_y=mag.y_off,
    hard_iron_z=mag.z_off,
    soft_iron_x=mag.x_scale,
    soft_iron_y=mag.y_scale,
    soft_iron_z=mag.z_scale,
)
config.save()
print("Calibration saved to config zone.\n")

# Free memory before verification
gc.collect()

# Verify: reload config and apply to a fresh sensor
config2 = SteamiConfig(flash)
config2.load()

mag2 = LIS2MDL(i2c)
config2.apply_magnetometer_calibration(mag2)

print("Verification (5 heading readings after reload):")
for i in range(5):
    heading = mag2.heading()
    norm = mag2.calibrated_field()
    print("  Reading {}: heading={:.1f} deg  norm=({:.3f}, {:.3f}, {:.3f})".format(
        i + 1, heading, norm[0], norm[1], norm[2]))
    sleep_ms(500)

print("\nDone! Calibration is stored and will be restored at next boot.")
