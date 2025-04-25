import ssd1327

from machine import SPI, Pin

# Setup display on SPI bus
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)
# optical illusion - are the lines crooked?
display.fill(15)
sq = 12  # square size
seq = 100  # this magic number gives repititions of sequence 0,1,2,1... repeat
for y in range(0, display.height, sq + 1):
    offset = round(((seq & 3) / 3) * sq)
    seq >>= 2
    if seq == 0:
        seq = 100
    for x in range(0, display.width, sq * 2):
        display.framebuf.fill_rect(x + offset, y, sq, sq, 0)
    display.framebuf.hline(0, y + sq, display.width, 6)
display.show()
