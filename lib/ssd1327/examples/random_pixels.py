import ssd1327
import uos

from machine import SPI, Pin

# Setup display on SPI bus
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)
# random pixels (slow)
# note: urandom not available on all devices

for i in range(256):
    x = uos.urandom(1)[0] // 2
    y = uos.urandom(1)[0] // 2
    display.pixel(x, y, 15)
    display.show()
