import ssd1327
from time import sleep
from machine import SPI, Pin

# Setup display on SPI bus
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)

# scroll the framebuf down 16px
# note: does not wrap around
display.fill(0)
for i in range(10):
    display.text("line {}".format(i), 40, i * 8, 15)
display.show()
sleep(1)

for i in range(2):
    display.scroll(0, 16)  # framebuf.scroll
    display.show()
    sleep(1)
