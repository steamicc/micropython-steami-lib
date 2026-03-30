"""Calibrate ISM330DL accelerometer bias and save to persistent config.

This example measures accelerometer offsets while the board is lying flat.
The computed offsets (ox, oy, oz) are stored in the config zone and
survive power cycles.

Instructions:
- Place the board flat and still (screen up)
- Wait for measurement
"""

from time import sleep_ms

from daplink_bridge import DaplinkBridge
from ism330dl import ISM330DL
from machine import I2C
from steami_config import SteamiConfig

# --- Init ---
print("Initializing...")

i2c = I2C(1)
print("I2C initialized.")
bridge = DaplinkBridge(i2c)
print("DaplinkBridge initialized.")
config = SteamiConfig(bridge)
print("SteamiConfig initialized.")
config.load()

print("Initialization complete.\n")
imu = ISM330DL(i2c)

print("=== Accelerometer Calibration ===\n")
print("Place the board flat (screen up) and keep it still...")
sleep_ms(2000)

# --- Step 1: Collect samples ---

samples = 100
sx = sy = sz = 0.0

for _i in range(samples):
    ax, ay, az = imu.acceleration_g()
    sx += ax
    sy += ay
    sz += az
    sleep_ms(20)

ax = sx / samples
ay = sy / samples
az = sz / samples

# Expected: (0, 0, -1g) when flat (screen up)
ox = ax
oy = ay
oz = az + 1.0  # compensate gravity

print("\nMeasured average:")
print("  ax = {:.3f} g".format(ax))
print("  ay = {:.3f} g".format(ay))
print("  az = {:.3f} g".format(az))

print("\nComputed offsets:")
print("  ox = {:.3f}".format(ox))
print("  oy = {:.3f}".format(oy))
print("  oz = {:.3f}".format(oz))

# --- Step 2: Save ---

config.set_accelerometer_calibration(ox=ox, oy=oy, oz=oz)
config.save()

print("\nCalibration saved to config zone.")

# --- Step 3: Verify ---

config2 = SteamiConfig(bridge)
config2.load()

imu2 = ISM330DL(i2c)
config2.apply_accelerometer_calibration(imu2)

print("\nVerification (5 readings):")

for i in range(5):
    ax, ay, az = imu2.acceleration_g()

    # Apply offsets manually (driver not patched yet)
    ox = getattr(imu2, "_accel_offset_x", 0.0)
    oy = getattr(imu2, "_accel_offset_y", 0.0)
    oz = getattr(imu2, "_accel_offset_z", 0.0)

    ax -= ox
    ay -= oy
    az -= oz

    print("  {}: ax={:.3f} ay={:.3f} az={:.3f}".format(i + 1, ax, ay, az))
    sleep_ms(500)

print("\nDone! Calibration will persist across reboots.")
