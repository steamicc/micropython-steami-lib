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
sleep(1)

# more dark shades
display.lookup([0, 2, 3, 4, 5, 6, 7, 8, 10, 13, 16, 19, 22, 25, 28])
sleep(1)

# more light shades
display.lookup([0, 2, 5, 8, 11, 14, 16, 19, 22, 23, 24, 25, 26, 27, 28])
sleep(1)

# steps
display.lookup([0, 2, 3, 6, 7, 10, 11, 14, 15, 19, 20, 23, 24, 27, 28])
sleep(1)

# even more dark shades
display.lookup([0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 20, 28])
sleep(1)

# revert to default linear scale
display.write_cmd(0xB9)
sleep(1)
