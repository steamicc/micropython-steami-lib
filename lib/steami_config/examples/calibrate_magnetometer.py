"""Calibrate the LIS2MDL magnetometer and save to persistent config.

This example runs a 3D min/max calibration by collecting samples while
the user rotates the board in all directions.  The computed hard-iron
offsets and soft-iron scale factors are stored in the config zone and
survive power cycles.

Instructions and a countdown are displayed on the SSD1327 OLED screen.
Press MENU to start the calibration.
"""

import gc
from time import sleep_ms

from daplink_flash import DaplinkFlash
from lis2mdl import LIS2MDL
from machine import I2C, SPI, Pin
from ssd1327 import WS_OLED_128X128_SPI
from steami_config import SteamiConfig

# --- Hardware init ---

i2c = I2C(1)
oled = WS_OLED_128X128_SPI(
    SPI(1),
    Pin("DATA_COMMAND_DISPLAY"),
    Pin("RST_DISPLAY"),
    Pin("CS_DISPLAY"),
)
btn_menu = Pin("MENU_BUTTON", Pin.IN, Pin.PULL_UP)

flash = DaplinkFlash(i2c)
config = SteamiConfig(flash)
config.load()
mag = LIS2MDL(i2c)
config.apply_magnetometer_calibration(mag)


# --- Helper functions ---


def show(lines):
    """Display centered text lines on the round OLED screen."""
    oled.fill(0)
    th = len(lines) * 12
    ys = max(0, (128 - th) // 2)
    for i, line in enumerate(lines):
        x = max(0, (128 - len(line) * 8) // 2)
        oled.text(line, x, ys + i * 12, 15)
    oled.show()


def draw_degree(x, y, col=15):
    """Draw a tiny degree symbol (3x3 circle) at pixel position."""
    oled.pixel(x + 1, y, col)
    oled.pixel(x, y + 1, col)
    oled.pixel(x + 2, y + 1, col)
    oled.pixel(x + 1, y + 2, col)


def wait_menu():
    """Wait for MENU button press then release."""
    while btn_menu.value() == 1:
        sleep_ms(10)
    while btn_menu.value() == 0:
        sleep_ms(10)


# --- Step 1: Display instructions and wait for MENU ---

print("=== Magnetometer Calibration ===\n")
print("Current offsets:  x={:.1f}  y={:.1f}  z={:.1f}".format(
    mag.x_off, mag.y_off, mag.z_off))
print("Current scales:   x={:.3f}  y={:.3f}  z={:.3f}\n".format(
    mag.x_scale, mag.y_scale, mag.z_scale))

show([
    "COMPAS",
    "",
    "Tournez la",
    "carte dans",
    "toutes les",
    "directions",
    "",
    "MENU = demarrer",
])

print("Press MENU to start calibration...")
wait_menu()
print("Starting calibration...\n")

# --- Step 2: Acquisition with countdown ---

samples = 600
delay = 20
total_sec = (samples * delay) // 1000
xmin = ymin = zmin = 1e9
xmax = ymax = zmax = -1e9

for s in range(samples):
    x, y, z = mag.magnetic_field()
    xmin = min(xmin, x)
    xmax = max(xmax, x)
    ymin = min(ymin, y)
    ymax = max(ymax, y)
    zmin = min(zmin, z)
    zmax = max(zmax, z)
    if s % 50 == 0:
        remain = total_sec - (s * delay) // 1000
        show([
            "COMPAS",
            "",
            "Acquisition...",
            "",
            "Continuez a",
            "tourner",
            "",
            "{} sec".format(remain),
        ])
    sleep_ms(delay)

mag.x_off = (xmax + xmin) / 2.0
mag.y_off = (ymax + ymin) / 2.0
mag.z_off = (zmax + zmin) / 2.0
mag.x_scale = (xmax - xmin) / 2.0 or 1.0
mag.y_scale = (ymax - ymin) / 2.0 or 1.0
mag.z_scale = (zmax - zmin) / 2.0 or 1.0

print("Calibration complete!")
print("  Hard-iron offsets: x={:.1f}  y={:.1f}  z={:.1f}".format(
    mag.x_off, mag.y_off, mag.z_off))
print("  Soft-iron scales:  x={:.3f}  y={:.3f}  z={:.3f}\n".format(
    mag.x_scale, mag.y_scale, mag.z_scale))

# --- Step 3: Save to config zone ---

show(["COMPAS", "", "Sauvegarde..."])

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
sleep_ms(500)

# --- Step 4: Verify ---

show(["COMPAS", "", "Sauvegarde OK", "", "Verification..."])

gc.collect()
config2 = SteamiConfig(flash)
config2.load()

mag2 = LIS2MDL(i2c)
config2.apply_magnetometer_calibration(mag2)

print("Verification (5 heading readings after reload):")
result_lines = ["COMPAS", "", "Resultats:"]
for i in range(5):
    heading = mag2.heading_flat_only()
    line = "  {}: cap={:.0f}".format(i + 1, heading)
    print("  Reading {}: heading={:.1f} deg".format(i + 1, heading))
    result_lines.append(line)
    sleep_ms(500)

result_lines.append("")
result_lines.append("Termine !")

# Draw results with degree symbols
oled.fill(0)
th = len(result_lines) * 12
ys = max(0, (128 - th) // 2)
for i, line in enumerate(result_lines):
    x = max(0, (128 - len(line) * 8) // 2)
    oled.text(line, x, ys + i * 12, 15)
    if "cap=" in line:
        draw_degree(x + len(line) * 8 + 1, ys + i * 12)
oled.show()

print("\nDone! Calibration is stored and will be restored at next boot.")
