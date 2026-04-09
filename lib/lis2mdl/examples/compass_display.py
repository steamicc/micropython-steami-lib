"""Digital compass example using LIS2MDL and Steami Screen OLED widget.

Reads the magnetic heading using the built-in flat heading method,
and draws a dynamic compass on the display using the Screen widget.
Includes a preliminary 3D calibration step.
"""

from time import sleep_ms

import ssd1327
from lis2mdl import LIS2MDL
from machine import I2C, SPI, Pin
from steami_screen import Screen, SSD1327Display

# Layout Constants for Calibration Screen
CALIB_MSG1_X = 12
CALIB_MSG1_Y = 50
CALIB_MSG2_X = 4
CALIB_MSG2_Y = 70

# Hardware Initialization
i2c = I2C(1)
mag = LIS2MDL(i2c)

spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

# Initialize the raw display, then wrap it in the high-level Screen widget system
raw_display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)
display = SSD1327Display(raw_display)
screen = Screen(display)

try:
    # Calibration Phase
    raw_display.fill(0)
    raw_display.text("Calibrating...", CALIB_MSG1_X, CALIB_MSG1_Y, 15)
    raw_display.text("Move in 8-shape", CALIB_MSG2_X, CALIB_MSG2_Y, 15)
    raw_display.show()
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
    # Clean up and power off display on exit
    screen.clear()
    screen.show()
    sleep_ms(100)
    raw_display.power_off()
