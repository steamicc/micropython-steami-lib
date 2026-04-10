"""
Displays APDS9960 ambient light with a scrolling line graph.
"""

from time import sleep_ms

import ssd1327
from apds9960 import uAPDS9960 as APDS9960
from machine import I2C, SPI, Pin
from steami_screen import Screen, SSD1327Display

# --- Display setup ---
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

raw_display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)
display = SSD1327Display(raw_display)
screen = Screen(display)

# --- Sensor setup ---
i2c = I2C(1)
apds = APDS9960(i2c)

# --- Data buffer (scrolling window) ---
MAX_POINTS = 20
data = []

# --- Main loop ---
while True:
    lux = apds.ambient_light()
    data.append(lux)
    if len(data) > MAX_POINTS:
        data.pop(0)

    screen.clear()
    screen.title("Light (lux)")
    screen.graph(data, min_val=0, max_val=1000)
    screen.subtitle("APDS9960", "20s window")
    screen.show()

    sleep_ms(1000)
