import ssd1327
from time import sleep
from machine import SPI, Pin

# Setup display on SPI bus
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)

# from top left
display.fill(0)
x1 = 0
y1 = 0
y2 = display.height - 1
for x2 in range(0, display.width + 1, 8):
    display.framebuf.line(x1, y1, x2, y2, 15)
    display.show()
x2 = display.width - 1
for y2 in range(0, display.height + 1, 8):
    display.framebuf.line(x1, y1, x2, y2, 15)
    display.show()
sleep(1)

# from top right
display.fill(0)
x1 = display.width - 1
y1 = 0
y2 = display.height - 1
for x2 in range(0, display.width + 1, 8):
    display.framebuf.line(x1, y1, x2, y2, 15)
    display.show()
x2 = 0
for y2 in range(0, display.height + 1, 8):
    display.framebuf.line(x1, y1, x2, y2, 15)
    display.show()
sleep(1)

# from bottom left
display.fill(0)
x1 = 0
y1 = display.height - 1
y2 = 0
for x2 in range(0, display.width + 1, 8):
    display.framebuf.line(x1, y1, x2, y2, 15)
    display.show()
x2 = display.width - 1
for y2 in range(0, display.height + 1, 8):
    display.framebuf.line(x1, y1, x2, y2, 15)
    display.show()
sleep(1)

# from bottom right
display.fill(0)
x1 = display.width - 1
y1 = display.height - 1
y2 = 0
for x2 in range(0, display.width + 1, 8):
    display.framebuf.line(x1, y1, x2, y2, 15)
    display.show()
x2 = 0
for y2 in range(0, display.height + 1, 8):
    display.framebuf.line(x1, y1, x2, y2, 15)
    display.show()
sleep(1)
