"""Calibrate the LIS2MDL magnetometer and save to persistent config.

This example runs a 3D min/max calibration by collecting samples while
the user rotates the board in all directions.  The computed hard-iron
offsets and soft-iron scale factors are stored in the config zone and
survive power cycles.

Instructions are displayed on the SSD1327 OLED screen when available.

Usage:
    mpremote mount lib/ run lib/steami_config/examples/calibrate_magnetometer.py

When prompted, slowly rotate the board in all directions (tilt, roll,
yaw) for about 12 seconds.  The script then saves the calibration and
verifies it by displaying corrected heading readings.
"""

import gc
import sys
from time import sleep_ms

from machine import I2C

# Add driver paths when running via mpremote mount lib/
for p in ("daplink_flash", "steami_config", "lis2mdl", "ssd1327"):
    path = "/remote/" + p
    if path not in sys.path:
        sys.path.insert(0, path)


def show_screen(i2c, lines):
    """Display text lines on the OLED screen, then free the driver."""
    try:
        from ssd1327.device import WS_OLED_128X128_I2C

        oled = WS_OLED_128X128_I2C(i2c)
        oled.fill(0)
        for i, line in enumerate(lines):
            oled.text(line, 0, i * 12, 15)
        oled.show()
        del oled
    except Exception:
        pass
    sys.modules.pop("ssd1327.device", None)
    gc.collect()


i2c = I2C(1)

# --- Step 1: Load config and magnetometer ---

from daplink_flash.device import DaplinkFlash  # noqa: E402
from steami_config.device import SteamiConfig  # noqa: E402

flash = DaplinkFlash(i2c)
config = SteamiConfig(flash)
config.load()

from lis2mdl.device import LIS2MDL  # noqa: E402

mag = LIS2MDL(i2c)

# Show current state
print("=== Magnetometer Calibration ===\n")
print("Current offsets:  x={:.1f}  y={:.1f}  z={:.1f}".format(
    mag.x_off, mag.y_off, mag.z_off))
print("Current scales:   x={:.3f}  y={:.3f}  z={:.3f}\n".format(
    mag.x_scale, mag.y_scale, mag.z_scale))

# --- Step 2: Display instructions on screen ---

show_screen(i2c, [
    "=== COMPAS ===",
    "",
    "Calibration du",
    "magnetometre",
    "",
    "Tournez la carte",
    "dans toutes les",
    "directions...",
    "",
    "12 secondes",
])

print("Rotate the board slowly in ALL directions for 12 seconds...")
print("(tilt, roll, turn upside down, spin...)\n")
sleep_ms(2000)

# --- Step 3: Run 3D calibration ---

show_screen(i2c, [
    "=== COMPAS ===",
    "",
    "Acquisition...",
    "",
    "Continuez a",
    "tourner la carte",
])

mag.calibrate_minmax_3d(samples=600, delay_ms=20)

print("Calibration complete!")
print("  Hard-iron offsets: x={:.1f}  y={:.1f}  z={:.1f}".format(
    mag.x_off, mag.y_off, mag.z_off))
print("  Soft-iron scales:  x={:.3f}  y={:.3f}  z={:.3f}\n".format(
    mag.x_scale, mag.y_scale, mag.z_scale))

# --- Step 4: Save to config zone ---

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

show_screen(i2c, [
    "=== COMPAS ===",
    "",
    "Calibration",
    "sauvegardee !",
    "",
    "Verification...",
])

# --- Step 5: Verify ---

gc.collect()
config2 = SteamiConfig(flash)
config2.load()

mag2 = LIS2MDL(i2c)
config2.apply_magnetometer_calibration(mag2)

print("Verification (5 heading readings after reload):")
lines = ["=== COMPAS ===", "", "Verification:"]
for i in range(5):
    heading = mag2.heading_flat_only()
    norm = mag2.calibrated_field()
    line = "  {}: cap={:.0f} deg".format(i + 1, heading)
    print("  Reading {}: heading={:.1f} deg  norm=({:.3f}, {:.3f}, {:.3f})".format(
        i + 1, heading, norm[0], norm[1], norm[2]))
    lines.append(line)
    sleep_ms(500)

show_screen(i2c, lines + ["", "Termine !"])  # noqa: RUF005
print("\nDone! Calibration is stored and will be restored at next boot.")
