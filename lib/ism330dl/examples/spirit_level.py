"""Spirit level example using ISM330DL accelerometer and the board screen.

Displays a digital bubble level. The bubble moves according to the board's tilt.
When the board is perfectly flat, the bubble centers and the background lights up.

The screen is steami.Screen: the SSD1327 OLED on V1a/V1b, the round GC9A01
TFT on V1c. The layout is given for 128 px and scaled with screen.u().

On startup, the board must be placed on a flat surface for a brief auto-zero
calibration (averages a few samples to compensate accelerometer bias).
"""

from time import sleep_ms

from ism330dl import ISM330DL
from machine import I2C
from steami import Screen
from steami_screen import BLACK, WHITE

# --- Hardware Initialization ---

screen = Screen()
screen.begin()  # allocate the frame buffer early in the program

i2c = I2C(1)
imu = ISM330DL(i2c)

# Layout & Physics Constants (8, 50 and 20 are 128 px units)
SCREEN_SIZE = screen.width
SCREEN_CENTER_X, SCREEN_CENTER_Y = screen.center
BUBBLE_RADIUS = screen.u(8)

# Maximum pixel distance the bubble can travel from the center
MAX_OFFSET = screen.u(50)

# Half length of the crosshair arms
CROSS_HALF = screen.u(20)

# Gap between the bubble and the target square
TARGET_GAP = screen.u(2)

# Stroke width: 1 px on 128 px, 2 px on 240 px
STROKE = screen.k

# Tilt thresholds (in g) to consider the board "level/flat"
LEVEL_THRESHOLD = 0.05

# Auto-zero calibration: number of samples averaged at startup
CAL_SAMPLES = 20
CAL_DELAY_MS = 50

# Display Colors (RGB; grey level 4 of 15 on the SSD1327 when level)
COLOR_BG_TILTED = BLACK
COLOR_BG_LEVEL = (68, 68, 68)
COLOR_FG = WHITE

# Loop delay
POLL_RATE_MS = 20


# --- Auto-zero calibration ---
# Average N acceleration samples to compensate the board's bias at rest.
# The board must be on a flat surface during this phase.

print("=======================")
print("     Spirit Level      ")
print("=======================")
print("Calibrating... keep the board flat and still.")

cal_ax, cal_ay = 0.0, 0.0
for _ in range(CAL_SAMPLES):
    ax, ay, _az = imu.acceleration_g()
    cal_ax += ax
    cal_ay += ay
    sleep_ms(CAL_DELAY_MS)
cal_ax /= CAL_SAMPLES
cal_ay /= CAL_SAMPLES
print("Offset: ax={:.3f}g, ay={:.3f}g".format(cal_ax, cal_ay))

print("Tilt the board to move the bubble.")
print("Press Ctrl+C to exit.")

try:
    while True:
        # Read acceleration in g-forces, subtract startup bias
        raw_ax, raw_ay, _az = imu.acceleration_g()
        ax = raw_ax - cal_ax
        ay = raw_ay - cal_ay

        # Level Detection
        # If both X and Y axes are close to 0g, the board is flat
        is_level = abs(ax) < LEVEL_THRESHOLD and abs(ay) < LEVEL_THRESHOLD

        bg_color = COLOR_BG_LEVEL if is_level else COLOR_BG_TILTED

        # Map Acceleration to Pixel Offset
        # We cap the acceleration at 1.0g to avoid the bubble leaving the screen
        clamped_ax = max(-1.0, min(1.0, ax))
        clamped_ay = max(-1.0, min(1.0, ay))

        # Axis Mapping & Inversion:
        # We swap X and Y to match the display's physical orientation.
        # The negative sign on 'ay' inverts the axis so the indicator
        # behaves like a physical air bubble (moving to the highest point).
        offset_x = int(-clamped_ay * MAX_OFFSET)
        offset_y = int(clamped_ax * MAX_OFFSET)

        bubble_x = SCREEN_CENTER_X + offset_x
        bubble_y = SCREEN_CENTER_Y + offset_y

        bubble_x = max(BUBBLE_RADIUS, min(SCREEN_SIZE - 1 - BUBBLE_RADIUS, bubble_x))
        bubble_y = max(BUBBLE_RADIUS, min(SCREEN_SIZE - 1 - BUBBLE_RADIUS, bubble_y))

        # Drawing Phase
        screen.clear(bg_color)

        # Draw the crosshair (Target reference)
        screen.rect(SCREEN_CENTER_X - CROSS_HALF, SCREEN_CENTER_Y,
                    2 * CROSS_HALF, STROKE, COLOR_FG, fill=True)
        screen.rect(SCREEN_CENTER_X, SCREEN_CENTER_Y - CROSS_HALF,
                    STROKE, 2 * CROSS_HALF, COLOR_FG, fill=True)

        # Draw the center square (Target zone), STROKE px wide
        half = BUBBLE_RADIUS + TARGET_GAP
        for i in range(STROKE):
            screen.rect(SCREEN_CENTER_X - half + i, SCREEN_CENTER_Y - half + i,
                        2 * (half - i), 2 * (half - i), COLOR_FG)

        # Draw the actual bubble
        screen.circle(bubble_x, bubble_y, BUBBLE_RADIUS, COLOR_FG, fill=True)

        screen.show()
        sleep_ms(POLL_RATE_MS)

except KeyboardInterrupt:
    print("\nSpirit level stopped.")
finally:
    # Clean up: blank the screen and power off the IMU to avoid battery drain
    screen.clear()
    screen.show()
    imu.power_off()
