import ssd1327

from machine import SPI, Pin

# Setup display on SPI bus
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)

# rects using framebuf
display.fill(0)
for i in range(15):
    j = 8 * i
    display.framebuf.fill_rect(j, j, 8, 8, i)
    display.framebuf.rect(120 - (j), j, 8, 8, i)
display.show()
