import ssd1327
from time import sleep
from machine import SPI, Pin

# Setup display on SPI bus
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)

# corner pixels
display.fill(0)
maxw = display.width - 1
maxh = display.height - 1
display.pixel(0, 0, 15)  # TL
display.pixel(0, maxh, 15)  # TR
display.pixel(maxw, maxh, 15)  # BR
display.pixel(maxw, 0, 15)  # BL
display.show()
sleep(1)


# diagonal line pixel by pixel (the slow way)
display.fill(0)
w = display.width
for i in range(w):
    display.pixel(i, i, 15)
    display.pixel(w - i, i, 15)
display.show()
sleep(1)
