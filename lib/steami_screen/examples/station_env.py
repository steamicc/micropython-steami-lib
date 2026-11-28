"""Climate station: temperature, humidity and pressure with a comfort index.

Displays live readings with a comfort index on the board screen using
steami_screen widgets.

Runs on every release, the steami classes pick the sensors and the screen:
    - V1a/V1b: WSEN-HIDS (temperature, humidity), WSEN-PADS (pressure),
      SSD1327 128x128 OLED
    - V1c: BME280 (temperature, humidity, pressure), GC9A01 240x240 TFT
"""

import math
from time import sleep_ms

from steami import Humidity, Pressure, Screen, Temperature
from steami_screen import GRAY, GREEN, LIGHT, RED, WHITE

# --- Display ---
screen = Screen()
screen.begin()  # allocate the frame buffer early in the program

# --- Sensors ---
temperature = Temperature()
humidity = Humidity()
pressure = Pressure()
for sensor in (temperature, humidity, pressure):
    sensor.begin()

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
    screen.gauge(int(temp), min_val=0, max_val=50, color=color)
    screen.title("CLIMATE")
    screen.value("{:.1f}".format(temp), unit="C")
    screen.subtitle(
        "H:{:.0f}%  P:{:.0f}hPa".format(hum, pres),
        label,
    )
    screen.show()


def draw_missing():
    """Render one frame when a sensor gives no value."""
    screen.clear()
    screen.title("CLIMATE")
    screen.value("--", unit="C")
    screen.subtitle("no sensor value")
    screen.show()


# --- Main loop ---
print("Climate station started")
print("Press Ctrl+C to exit.")

try:
    while True:
        temp = temperature.read()
        hum = humidity.read()
        pres = pressure.read()
        if math.isnan(temp) or math.isnan(hum) or math.isnan(pres):
            # A sensor did not answer: the library printed why, once.
            draw_missing()
        else:
            hum = max(0.0, min(100.0, hum))
            print("T:{:.1f}C  H:{:.1f}%  P:{:.0f}hPa".format(temp, hum, pres))
            draw_screen(temp, hum, pres)
        sleep_ms(POLL_MS)
except KeyboardInterrupt:
    print("\nClimate station stopped.")
finally:
    screen.clear()
    screen.show()
