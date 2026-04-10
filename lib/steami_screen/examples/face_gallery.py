"""
Cycle through all 6 built-in face expressions.
"""

from time import sleep_ms

import ssd1327
from machine import SPI, Pin
from steami_screen import Screen, SSD1327Display

# --- Display setup ---
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

raw_display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)
display = SSD1327Display(raw_display)
screen = Screen(display)

faces = [
    ("happy", "HAPPY"),
    ("sad", "SAD"),
    ("surprised", "SURPRISED"),
    ("sleeping", "SLEEPING"),
    ("angry", "ANGRY"),
    ("love", "LOVE"),
]

compact = True

while True:
    compact = not compact
    for expression, label in faces:
        screen.clear()
        screen.face(expression, compact=compact)
        screen.show()
        print("Showing face:", label, "Compact:", compact)
        sleep_ms(1000)
