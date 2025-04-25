import ssd1327

from machine import SPI, Pin

# Setup display on SPI bus
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)
# 15 shades of grey
display.fill(0)
for r in range(16):
    display.framebuf.fill_rect(0, r * 8, 128, 8, r)
display.show()
