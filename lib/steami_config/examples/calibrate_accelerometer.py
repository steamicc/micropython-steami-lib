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

i2c = I2C(1)
bridge = DaplinkBridge(i2c)
config = SteamiConfig(bridge)
config.load()

imu = ISM330DL(i2c)

print("=== Accelerometer Calibration ===\n")
print("Place the board flat (screen up) and keep it still...")
sleep_ms(2000)

# --- Step 1: Collect samples ---

samples = 100
sx = sy = sz = 0.0

for _ in range(samples):
    ax, ay, az = imu.acceleration_g()
    sx += ax
    sy += ay
    sz += az
    sleep_ms(20)

ax = sx / samples
ay = sy / samples
az = sz / samples

# Expected resting orientation: flat, screen up -> (0, 0, -1g)
ox = ax
oy = ay
oz = az + 1.0
# Flat, screen up → expected (0,0,-1g), so Z offset = measured - (-1g) = az + 1.0
# because gravity points downward while the sensor Z axis is defined positive downward

print("\nMeasured average:")
print("  ax = {:.3f} g".format(ax))
print("  ay = {:.3f} g".format(ay))
print("  az = {:.3f} g".format(az))

print("\nComputed offsets:")
print("  ox = {:.3f} g".format(ox))
print("  oy = {:.3f} g".format(oy))
print("  oz = {:.3f} g".format(oz))

# --- Step 2: Save to config zone ---

config.set_accelerometer_calibration(ox=ox, oy=oy, oz=oz)
config.save()

print("\nCalibration saved to config zone.")

# --- Step 3: Verify after reload ---

config2 = SteamiConfig(bridge)
config2.load()

imu2 = ISM330DL(i2c)
config2.apply_accelerometer_calibration(imu2)

print("\nApplied offsets after reload:")
ox2, oy2, oz2 = imu2.get_accel_offset()
print("  ox = {:.3f} g".format(ox2))
print("  oy = {:.3f} g".format(oy2))
print("  oz = {:.3f} g".format(oz2))

print("\nVerification (5 corrected readings):")
for i in range(5):
    ax, ay, az = imu2.acceleration_g()
    print("  {}: ax={:.3f} ay={:.3f} az={:.3f}".format(i + 1, ax, ay, az))
    sleep_ms(500)

print("\nDone! Calibration is stored and will be restored at next boot.")
