"""Color lamp example using APDS9960 and SSD1327 OLED.

Detects the color of an object placed near the APDS9960 sensor.
Includes an auto-calibration phase for ambient room light.
Displays the dominant color and raw RGBC values on a round OLED layout.
The background brightness matches the ambient light intensity dynamically.
"""

from time import sleep_ms

import ssd1327
from apds9960 import uAPDS9960 as APDS9960
from machine import I2C, SPI, Pin

# Layout Constants
MIN_CLEAR = 10
DOMINANCE_THRESHOLD = 3  # Threshold to prevent color flickering
TITLE_Y = 24
TITLE_X = 28
COLOR_Y = 40
COLOR_X = 44
GRID_ROW1_Y = 70
GRID_ROW2_Y = 90
GRID_COL1_X = 20
GRID_COL2_X = 72

# Calibration Constants
CALIB_TEXT1_X = 12
CALIB_TEXT1_Y = 54
CALIB_TEXT2_X = 16
CALIB_TEXT2_Y = 74
CALIB_COLOR = 15
CALIB_BASELINE = 50
CALIB_SAMPLES = 30
CALIB_DELAY_MS = 100
CALIB_BUFFER_DIVISOR = 10

# Hardware Initialization
i2c = I2C(1)
apds = APDS9960(i2c)
apds.enable_light_sensor()
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")
display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)

print("=======================")
print("      Color Lamp       ")
print("=======================")
print("Press Ctrl+C to exit.")

try:
    # Auto-Calibration Phase
    print("Calibrating ambient light... Leave the sensor uncovered.")
    display.fill(0)
    display.text("Calibrating...", CALIB_TEXT1_X, CALIB_TEXT1_Y, CALIB_COLOR)
    display.text("Do not cover", CALIB_TEXT2_X, CALIB_TEXT2_Y, CALIB_COLOR)
    display.show()

    total_c = 0
    # Sample light using an average for better robustness against noise
    for _ in range(CALIB_SAMPLES):
        total_c += apds.ambient_light()
        sleep_ms(CALIB_DELAY_MS)

    avg_clear_calib = total_c // CALIB_SAMPLES

    # Add a small buffer to the max calibration so it doesn't max out too easily
    max_clear_limit = avg_clear_calib + (avg_clear_calib // CALIB_BUFFER_DIVISOR)

    if max_clear_limit <= 0:
        max_clear_limit = 1  # Prevent division by zero in case of very low light

    print("Calibration complete. Limit set to:", max_clear_limit)
    sleep_ms(500)

    # Main Loop
    while True:
        # Read RGBC values from the sensor
        c = apds.ambient_light()
        r = apds.red_light()
        g = apds.green_light()
        b = apds.blue_light()

        # Determine background greyscale intensity (0 to 15)
        clamped_c = max(MIN_CLEAR, min(c, max_clear_limit))
        bg_color = (clamped_c * 15) // max_clear_limit

        # Determine text contrast (Dark text on light background, and vice-versa)
        text_color = 0 if bg_color > 7 else 15

        # Determine dominant color
        dominant_name = "DARK"
        if c > MIN_CLEAR:
            if r > g + DOMINANCE_THRESHOLD and r > b + DOMINANCE_THRESHOLD:
                dominant_name = "RED"
            elif g > r + DOMINANCE_THRESHOLD and g > b + DOMINANCE_THRESHOLD:
                dominant_name = "GREEN"
            elif b > r + DOMINANCE_THRESHOLD and b > g + DOMINANCE_THRESHOLD:
                dominant_name = "BLUE"
            else:
                dominant_name = "MIXED"

        # Drawing Phase
        display.fill(bg_color)

        display.text("Dominant:", TITLE_X, TITLE_Y, text_color)
        display.text(dominant_name, COLOR_X, COLOR_Y, text_color)

        # Draw Raw RGBC values in a 2x2 Grid
        display.text("R:{}".format(r), GRID_COL1_X, GRID_ROW1_Y, text_color)
        display.text("G:{}".format(g), GRID_COL2_X, GRID_ROW1_Y, text_color)
        display.text("B:{}".format(b), GRID_COL1_X, GRID_ROW2_Y, text_color)
        display.text("C:{}".format(c), GRID_COL2_X, GRID_ROW2_Y, text_color)

        display.show()
        sleep_ms(100)  # Slower poll rate to avoid screen flickering and make text readable

except KeyboardInterrupt:
    print("\nColor lamp stopped.")
finally:
    # Clean up hardware and power off display on exit
    apds.disable_light_sensor()
    display.fill(0)
    display.show()
    sleep_ms(100)
    display.power_off()
