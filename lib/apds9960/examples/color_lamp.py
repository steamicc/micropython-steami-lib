"""Color lamp example using APDS9960 and the board screen.

Detects the color of an object placed near the APDS9960 sensor.
Includes an auto-calibration phase for ambient room light.
Displays the dominant color and raw RGBC values on a round OLED layout.
The background brightness matches the ambient light intensity dynamically.

The screen is steami.Screen, so the drawing works on the SSD1327 OLED
(V1a/V1b) and the round GC9A01 TFT (V1c). The APDS-9960 itself is only on
V1a/V1b. The layout is given in 128 px units and scaled with screen.u().
"""

from time import sleep_ms

from apds9960 import uAPDS9960 as APDS9960
from machine import I2C
from steami import Screen
from steami_screen import BLACK, WHITE

# Board screen first: the frame buffer is allocated early in the program
screen = Screen()
screen.begin()

# Layout Constants (rows and columns in 128 px units)
MIN_CLEAR = 10
DOMINANCE_THRESHOLD = 3  # Threshold to prevent color flickering
TITLE_Y = 24
COLOR_Y = 40
GRID_ROW1_Y = 70
GRID_ROW2_Y = 90
GRID_COL1_X = 20
GRID_COL2_X = 72

# Calibration Constants
CALIB_TEXT1_Y = 54
CALIB_TEXT2_Y = 74
CALIB_COLOR = WHITE
CALIB_BASELINE = 50
CALIB_SAMPLES = 30
CALIB_DELAY_MS = 100
CALIB_BUFFER_DIVISOR = 10

# Hardware Initialization
i2c = I2C(1)
apds = APDS9960(i2c)
apds.enable_light_sensor()


def text_at(text, x, y, color):
    """Draw text with its top left at (x, y), in 128 px units."""
    screen.text(text, at=(screen.u(x), screen.u(y)), color=color)


def text_centered(text, y, color):
    """Draw text centred horizontally, its top at row y (128 px units)."""
    char_w = screen.width // screen.max_chars  # 8 px on 128 and on 240
    x = screen.width // 2 - len(text) * char_w // 2
    screen.text(text, at=(x, screen.u(y)), color=color)


print("=======================")
print("      Color Lamp       ")
print("=======================")
print("Press Ctrl+C to exit.")

try:
    # Auto-Calibration Phase
    print("Calibrating ambient light... Leave the sensor uncovered.")
    screen.clear()
    text_centered("Calibrating...", CALIB_TEXT1_Y, CALIB_COLOR)
    text_centered("Do not cover", CALIB_TEXT2_Y, CALIB_COLOR)
    screen.show()

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

        # Determine background greyscale intensity (0 to 15), as an RGB grey
        clamped_c = max(MIN_CLEAR, min(c, max_clear_limit))
        bg_level = (clamped_c * 15) // max_clear_limit
        bg_color = (bg_level * 17,) * 3

        # Determine text contrast (Dark text on light background, and vice-versa)
        text_color = BLACK if bg_level > 7 else WHITE

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
        screen.clear(bg_color)

        text_centered("Dominant:", TITLE_Y, text_color)
        text_centered(dominant_name, COLOR_Y, text_color)

        # Draw Raw RGBC values in a 2x2 Grid
        text_at("R:{}".format(r), GRID_COL1_X, GRID_ROW1_Y, text_color)
        text_at("G:{}".format(g), GRID_COL2_X, GRID_ROW1_Y, text_color)
        text_at("B:{}".format(b), GRID_COL1_X, GRID_ROW2_Y, text_color)
        text_at("C:{}".format(c), GRID_COL2_X, GRID_ROW2_Y, text_color)

        screen.show()
        sleep_ms(100)  # Slower poll rate to avoid screen flickering and make text readable

except KeyboardInterrupt:
    print("\nColor lamp stopped.")
finally:
    # Clean up hardware and power off display on exit
    apds.disable_light_sensor()
    screen.clear()
    screen.show()
