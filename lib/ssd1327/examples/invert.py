import ssd1327

from machine import SPI, Pin
from time import sleep

# Setup display on SPI bus
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)
# greyscale lookup
display.fill(0)
for r in range(16):
    display.framebuf.fill_rect(0, r * 8, 128, 8, r)
display.show()

# invert greyscale lookup table
sleep(1)
display.invert(True)
sleep(1)
display.invert(False)
sleep(1)
