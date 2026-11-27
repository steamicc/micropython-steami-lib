"""Show the 16 colours of the GC9A01 palette on the STeaMi V1c screen."""

from gc9a01 import GC9A01
from machine import SPI, Pin

spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
cs = Pin("CS_DISPLAY")
rst = Pin("RST_DISPLAY")

display = GC9A01(spi, dc, cs, rst)
display.init()

# A 4 x 4 grid of 36 px squares, centred on the round screen.
for i in range(16):
    x = 48 + (i % 4) * 36
    y = 48 + (i // 4) * 36
    display.fill_rect(x, y, 34, 34, i)
    # Black numbers on light colours, white ones elsewhere.
    ink = 0 if i in (4, 5, 6, 9, 10, 12) else 5
    display.text(str(i), x + 2, y + 2, ink)

display.text("Palette", 92, 28, 5)
display.show()
