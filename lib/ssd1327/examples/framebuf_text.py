import ssd1327

from machine import SPI, Pin

# Setup display on SPI bus
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)

# greyscale ascii
display.fill(0)
for i in range(32, 128):
    j = i - 32
    x = (j % 16) << 3
    y = (j // 16) << 3
    display.text(chr(i), x, y + 40, 1 + (i % 15))
display.show()
