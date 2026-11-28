"""Calibrate the LIS2MDL magnetometer using the steami_screen UI.

This example walks through the full calibration flow:

- press MENU to start the calibration,
- rotate the board in all directions while samples are acquired,
- compute hard-iron offsets and soft-iron scale factors,
- save the calibration to persistent SteamiConfig storage,
- reload and verify the calibration survives a fresh config load.

Instructions and a countdown are displayed on the board screen
(steami.Screen: the SSD1327 OLED on V1a/V1b, the round GC9A01 TFT on V1c).
"""

import gc
from time import sleep_ms

from daplink_bridge import DaplinkBridge
from lis2mdl import LIS2MDL
from machine import I2C, Pin
from steami import Screen
from steami_config import SteamiConfig

# --- Hardware init ---

screen = Screen()
screen.begin()  # allocate the frame buffer early in the program

i2c = I2C(1)

btn_menu = Pin("MENU_BUTTON", Pin.IN, Pin.PULL_UP)

bridge = DaplinkBridge(i2c)
config = SteamiConfig(bridge)
config.load()

mag = LIS2MDL(i2c)
config.apply_magnetometer_calibration(mag)


# --- Helpers ---

def wait_menu():
    while btn_menu.value() == 1:
        sleep_ms(10)
    while btn_menu.value() == 0:
        sleep_ms(10)


def text_centered(text, y):
    """Draw text centred horizontally, its top at row y (real pixels)."""
    char_w = screen.width // screen.max_chars  # 8 px on 128 and on 240
    screen.text(text, at=(screen.width // 2 - len(text) * char_w // 2, y))


def text_rows(lines, y):
    """Draw centred lines from row y down, spaced by the text height.

    y is in 128 px units (scaled with screen.u), so that the block keeps its
    place inside the circle on 128 and 240 px.
    """
    y = screen.u(y)
    row_h = screen.text_height() + screen.u(3)
    for line in lines:
        text_centered(line, y)
        y += row_h


def show_intro():
    screen.clear()
    screen.title("COMPAS")

    text_rows(("Tournez la", "carte dans", "toutes les", "directions"), 36)
    screen.subtitle("MENU pour", "demarrer")

    screen.show()


def show_progress(remaining):
    screen.clear()
    screen.title("COMPAS")

    screen.value(remaining, unit="s", label="Acquisition...")
    screen.subtitle("Tournez", "la carte")

    screen.show()


def show_message(*lines):
    screen.clear()
    screen.title("COMPAS")
    screen.subtitle(*lines)
    screen.show()


def show_results(readings):
    screen.clear()
    screen.title("COMPAS")

    text_centered("Resultats:", screen.u(30))
    text_rows(["{}: {} deg".format(i + 1, int(h)) for i, h in enumerate(readings)], 42)
    screen.text("Termine !", at="S")
    screen.show()


# --- Step 1: Instructions ---

print("=== Magnetometer Calibration ===\n")

show_intro()

print("Press MENU to start calibration...")
wait_menu()
print("Starting calibration...\n")


# --- Step 2: Acquisition ---

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
        remaining = total_sec - (s * delay) // 1000
        show_progress(remaining)

    sleep_ms(delay)


# --- Compute calibration ---

mag.x_off = (xmax + xmin) / 2.0
mag.y_off = (ymax + ymin) / 2.0
mag.z_off = (zmax + zmin) / 2.0

mag.x_scale = (xmax - xmin) / 2.0 or 1.0
mag.y_scale = (ymax - ymin) / 2.0 or 1.0
mag.z_scale = (zmax - zmin) / 2.0 or 1.0

print("Calibration complete!")


# --- Step 3: Save ---

show_message("Sauvegarde...")

config.set_magnetometer_calibration(
    hard_iron_x=mag.x_off,
    hard_iron_y=mag.y_off,
    hard_iron_z=mag.z_off,
    soft_iron_x=mag.x_scale,
    soft_iron_y=mag.y_scale,
    soft_iron_z=mag.z_scale,
)

config.save()
sleep_ms(500)


# --- Step 4: Verify ---

show_message("Sauvegarde OK", "", "Verification...")

gc.collect()

config2 = SteamiConfig(bridge)
config2.load()

mag2 = LIS2MDL(i2c)
config2.apply_magnetometer_calibration(mag2)

print("Verification (5 readings):")

readings = []

for i in range(5):
    heading = mag2.heading_flat_only()
    readings.append(heading)

    screen.clear()
    screen.title("COMPAS")
    screen.value(int(heading), unit="deg", label="Mesure {}".format(i + 1))
    screen.show()

    print("Reading {}: {:.1f} deg".format(i + 1, heading))
    sleep_ms(500)


# --- Done ---

show_results(readings)

print("\nDone! Calibration stored.")
