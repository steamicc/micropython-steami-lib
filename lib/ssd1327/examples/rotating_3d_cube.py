import ssd1327

import math
from machine import SPI, Pin

# Setup display on SPI bus
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)

pi = math.pi

size = 700
width = display.width
height = display.height

d = 3
px = [-d, d, d, -d, -d, d, d, -d]
py = [-d, -d, d, d, -d, -d, d, d]
pz = [-d, -d, -d, -d, d, d, d, d]

p2x = [0, 0, 0, 0, 0, 0, 0, 0]
p2y = [0, 0, 0, 0, 0, 0, 0, 0]
r = [0, 0, 0]


def drawCube():
    r[0] = r[0] + pi / 180.0
    r[1] = r[1] + pi / 180.0
    r[2] = r[2] + pi / 180.0
    if r[0] >= 360.0 * pi / 180.0:
        r[0] = 0
    if r[1] >= 360.0 * pi / 180.0:
        r[1] = 0
    if r[2] >= 360.0 * pi / 180.0:
        r[2] = 0

    for i in range(8):
        px2 = px[i]
        py2 = math.cos(r[0]) * py[i] - math.sin(r[0]) * pz[i]
        pz2 = math.sin(r[0]) * py[i] + math.cos(r[0]) * pz[i]

        px3 = math.cos(r[1]) * px2 + math.sin(r[1]) * pz2
        py3 = py2
        pz3 = -math.sin(r[1]) * px2 + math.cos(r[1]) * pz2

        ax = math.cos(r[2]) * px3 - math.sin(r[2]) * py3
        ay = math.sin(r[2]) * px3 + math.cos(r[2]) * py3
        az = pz3 - 150

        p2x[i] = width / 2 + ax * size / az
        p2y[i] = height / 2 + ay * size / az

    display.fill(0)

    for i in range(3):
        display.framebuf.line(int(p2x[i]), int(p2y[i]), int(p2x[i + 1]), int(p2y[i + 1]), 1)
        display.framebuf.line(
            int(p2x[i + 4]), int(p2y[i + 4]), int(p2x[i + 5]), int(p2y[i + 5]), 1
        )
        display.framebuf.line(int(p2x[i]), int(p2y[i]), int(p2x[i + 4]), int(p2y[i + 4]), 1)

    display.framebuf.line(int(p2x[3]), int(p2y[3]), int(p2x[0]), int(p2y[0]), 1)
    display.framebuf.line(int(p2x[7]), int(p2y[7]), int(p2x[4]), int(p2y[4]), 1)
    display.framebuf.line(int(p2x[3]), int(p2y[3]), int(p2x[7]), int(p2y[7]), 1)
    display.show()


while True:
    drawCube()
