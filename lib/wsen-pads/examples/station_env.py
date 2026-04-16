"""Climate station example using WSEN-PADS, HTS221 and SSD1327 OLED.

Reads temperature and pressure from the WSEN-PADS sensor and humidity
from the HTS221 sensor. Displays live readings with a comfort index
on the round 128x128 OLED using steami_screen widgets.

Hardware:
    - WSEN-PADS (temperature + pressure)
    - HTS221 (humidity)
    - SSD1327 128x128 OLED display (round)
"""

from time import sleep_ms

import ssd1327
from hts221 import HTS221
from machine import I2C, SPI, Pin
from steami_screen import GRAY, GREEN, LIGHT, RED, WHITE, Screen, SSD1327Display
from wsen_pads import WSEN_PADS

# --- Display ---
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")
display = SSD1327Display(ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs))
screen = Screen(display)

# --- Sensors ---
i2c = I2C(1)
pads = WSEN_PADS(i2c)
hts = HTS221(i2c)

# --- Comfort thresholds ---
TEMP_MIN, TEMP_MAX = 18.0, 26.0
HUM_MIN, HUM_MAX = 40.0, 60.0
PRES_MIN, PRES_MAX = 1000.0, 1025.0

POLL_MS = 1000


def comfort_label(temp, hum, pres):
    """Return a (label, color) tuple describing indoor comfort."""
    if TEMP_MIN <= temp <= TEMP_MAX and HUM_MIN <= hum <= HUM_MAX and PRES_MIN <= pres <= PRES_MAX:
        return "IDEAL", GREEN
    if temp > 30 or hum > 75:
        return "HOT", RED
    if temp < 15 or hum < 25:
        return "COLD", GRAY
    if pres < PRES_MIN:
        return "LOW P", GRAY
    if pres > PRES_MAX:
        return "HIGH P", LIGHT
    return "OK", WHITE


def draw_screen(temp, hum, pres):
    """Render one frame with all readings and comfort index."""
    label, color = comfort_label(temp, hum, pres)

    screen.clear()
    screen.gauge(
        int(temp), min_val=0, max_val=50, color=color,
    )
    screen.title("CLIMATE")
    screen.value("{:.1f}".format(temp), unit="C")
    screen.subtitle(
        "H:{:.0f}%  P:{:.0f}hPa".format(hum, pres),
        label,
    )
    screen.show()


# --- Main loop ---
print("Climate station started")
print("Press Ctrl+C to exit.")

try:
    while True:
        temp = pads.temperature()
        hum = hts.humidity()
        pres = pads.pressure_hpa()
        hum = max(0.0, min(100.0, hum))
        print("T:{:.1f}C  H:{:.1f}%  P:{:.0f}hPa".format(temp, hum, pres))
        draw_screen(temp, hum, pres)
        sleep_ms(POLL_MS)
except KeyboardInterrupt:
    print("\nClimate station stopped.")
finally:
    screen.clear()
    screen.show()
    pads.power_off()
    hts.power_off()
