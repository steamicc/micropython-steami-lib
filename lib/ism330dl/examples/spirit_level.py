"""Spirit level example using ISM330DL accelerometer and SSD1327 OLED.

Displays a digital bubble level. The bubble moves according to the board's tilt.
When the board is perfectly flat, the bubble centers and the background lights up.

On startup, the board must be placed on a flat surface for a brief auto-zero
calibration (averages a few samples to compensate accelerometer bias).
"""

from time import sleep_ms

import ssd1327
from ism330dl import ISM330DL
from machine import I2C, SPI, Pin

# Layout & Physics Constants
SCREEN_SIZE = 128
SCREEN_CENTER_X = SCREEN_SIZE // 2
SCREEN_CENTER_Y = SCREEN_SIZE // 2
BUBBLE_RADIUS = 8

# Maximum pixel distance the bubble can travel from the center
MAX_OFFSET = 50

# Tilt thresholds (in g) to consider the board "level/flat"
LEVEL_THRESHOLD = 0.05

# Auto-zero calibration: number of samples averaged at startup
CAL_SAMPLES = 20
CAL_DELAY_MS = 50

# Display Colors (0 to 15 greyscale)
COLOR_BG_TILTED = 0
COLOR_BG_LEVEL = 4
COLOR_FG = 15

# Loop delay
POLL_RATE_MS = 20


def fill_circle(fbuf, x0, y0, r, c):
    """Helper to draw a filled circle since framebuf lacks it natively."""
    for y in range(-r, r + 1):
        for x in range(-r, r + 1):
            if x * x + y * y <= r * r:
                fbuf.pixel(x0 + x, y0 + y, c)


# --- Hardware Initialization ---

i2c = I2C(1)
imu = ISM330DL(i2c)

spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")
display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)

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
        display.fill(bg_color)

        # Draw the crosshair (Target reference)
        display.framebuf.hline(SCREEN_CENTER_X - 20, SCREEN_CENTER_Y, 40, COLOR_FG)
        display.framebuf.vline(SCREEN_CENTER_X, SCREEN_CENTER_Y - 20, 40, COLOR_FG)

        # Draw the center circle (Target zone)
        display.framebuf.rect(SCREEN_CENTER_X - BUBBLE_RADIUS - 2,
                              SCREEN_CENTER_Y - BUBBLE_RADIUS - 2,
                              (BUBBLE_RADIUS * 2) + 4,
                              (BUBBLE_RADIUS * 2) + 4,
                              COLOR_FG)

        # Draw the actual bubble
        fill_circle(display.framebuf, bubble_x, bubble_y, BUBBLE_RADIUS, COLOR_FG)

        display.show()
        sleep_ms(POLL_RATE_MS)

except KeyboardInterrupt:
    print("\nSpirit level stopped.")
finally:
    # Clean up: power off display and IMU to avoid battery drain
    display.fill(0)
    display.show()
    sleep_ms(100)
    display.power_off()
    imu.power_off()
