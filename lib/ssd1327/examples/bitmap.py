# draw a bitmap
# draw 16x15 smiley in horizontal mode
# .....#####...... 00 00 0F FF FF 00 00 00
# ...##.....##.... 00 0F F0 00 00 FF 00 00
# ..#.........#... 00 F0 00 00 00 00 F0 00
# .#...........#.. 0F 00 00 00 00 00 0F 00
# .#...........#.. 0F 00 00 00 00 00 0F 00
# ###############. FF FF FF FF FF FF FF F0
# #.#..####..##.#. F0 F0 0F FF F0 0F F0 F0
# #.#.###.#.###.#. F0 F0 FF F0 F0 FF F0 F0
# #..###...###..#. F0 0F FF 00 0F FF 00 F0
# #.............#. F0 00 00 00 00 00 00 F0
# .#........#..#.. 0F 00 00 00 00 F0 0F 00
# .#....####...#.. 0F 00 00 FF FF 00 0F 00
# ..#.........#... 00 F0 00 00 00 00 F0 00
# ...##.....##.... 00 0F F0 00 00 FF 00 00
# .....#####...... 00 00 0F FF FF 00 00 00

import ssd1327

from machine import SPI, Pin

# Setup display on SPI bus
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")

display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)

data = bytearray(
    [
        0x00,
        0x00,
        0x0F,
        0xFF,
        0xFF,
        0x00,
        0x00,
        0x00,
        0x00,
        0x0F,
        0xF0,
        0x00,
        0x00,
        0xFF,
        0x00,
        0x00,
        0x00,
        0xF0,
        0x00,
        0x00,
        0x00,
        0x00,
        0xF0,
        0x00,
        0x0F,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x0F,
        0x00,
        0x0F,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x0F,
        0x00,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xF0,
        0xF0,
        0xF0,
        0x0F,
        0xFF,
        0xF0,
        0x0F,
        0xF0,
        0xF0,
        0xF0,
        0xF0,
        0xFF,
        0xF0,
        0xF0,
        0xFF,
        0xF0,
        0xF0,
        0xF0,
        0x0F,
        0xFF,
        0x00,
        0x0F,
        0xFF,
        0x00,
        0xF0,
        0xF0,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0xF0,
        0x0F,
        0x00,
        0x00,
        0x00,
        0x00,
        0xF0,
        0x0F,
        0x00,
        0x0F,
        0x00,
        0x00,
        0xFF,
        0xFF,
        0x00,
        0x0F,
        0x00,
        0x00,
        0xF0,
        0x00,
        0x00,
        0x00,
        0x00,
        0xF0,
        0x00,
        0x00,
        0x0F,
        0xF0,
        0x00,
        0x00,
        0xFF,
        0x00,
        0x00,
        0x00,
        0x00,
        0x0F,
        0xFF,
        0xFF,
        0x00,
        0x00,
        0x00,
    ]
)

# remap so your data buffer wraps at the desired segment/pixel
# remapping does not modify the existing ram, instead gives you a window to supply new data
display.write_cmd(0x15)  # SET_COL_ADDR
display.write_cmd(0x00)  # start pos = 0
display.write_cmd(0x0F)  # start pos + half bitmap width (each byte is 2px wide) = 15
display.write_cmd(0x75)  # SET_ROW_ADDR
display.write_cmd(0x00)  # start pos = 0
display.write_cmd(0x1F)  # start + bitmap height = 15
display.write_data(data)


def bitmap(data, x, y, w, h):
    display.write_cmd(0x15)  # SET_COL_ADDR
    display.write_cmd(0x08 + (x // 2))
    display.write_cmd(0x08 + (x // 2) + (w // 2))
    display.write_cmd(0x75)  # SET_ROW_ADDR
    display.write_cmd(0x00 + y)
    display.write_cmd(y + h)
    display.write_data(data)


# draw many smileys
for y in range(8):
    for x in range(8):
        bitmap(data, x * 16, y * 16, 15, 15)
