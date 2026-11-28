"""Digital compass example using LIS2MDL and the steami_screen compass widget.

Reads the magnetic heading using the built-in flat heading method,
and draws a dynamic compass on the board screen using the Screen widget.
Includes a preliminary 3D calibration step.

The screen is steami.Screen: the SSD1327 OLED on V1a/V1b, the round GC9A01
TFT on V1c.
"""

from time import sleep_ms

from lis2mdl import LIS2MDL
from machine import I2C
from steami import Screen

# Hardware Initialization
screen = Screen()
screen.begin()  # allocate the frame buffer early in the program

i2c = I2C(1)
mag = LIS2MDL(i2c)

try:
    # Calibration Phase
    screen.clear()
    screen.title("COMPASS")
    screen.text("Calibrating...")
    screen.subtitle("Move in", "8-shape")
    screen.show()
    sleep_ms(100)

    print("Calibrate the magnetometer by moving it in a figure-eight pattern.")
    mag.calibrate_minmax_3d()
    print("Calibration complete.")

    # Main Compass Loop
    while True:
        heading_deg = mag.heading_flat_only()
        direction = mag.direction_label(heading_deg)

        # Drawing Phase (Delegated entirely to the steami_screen widget)
        screen.clear()
        screen.compass(heading_deg)
        screen.show()

        print("Angle: {:3.0f}° | Direction: {}".format(heading_deg, direction))

        sleep_ms(50)

except KeyboardInterrupt:
    pass
finally:
    # Clean up: blank the screen on exit
    screen.clear()
    screen.show()
