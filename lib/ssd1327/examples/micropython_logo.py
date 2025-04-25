import ssd1327

from machine import SPI, Pin

# Setup display on SPI bus
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)
# MicroPython logo
display.fill(0)
x = (display.width - 69) // 2
y = (display.height - 69) // 2
display.framebuf.fill_rect(x + 0, y + 0, 69, 69, 15)
display.framebuf.fill_rect(x + 15, y + 15, 3, 54, 0)
display.framebuf.fill_rect(x + 33, y + 0, 3, 54, 0)
display.framebuf.fill_rect(x + 51, y + 15, 3, 54, 0)
display.framebuf.fill_rect(x + 60, y + 56, 4, 7, 0)
display.show()
