import ssd1327

from machine import SPI, Pin
from time import sleep

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
sleep(1)

# rotate 180 degrees
# need to call show after rotating as rotating only sets the remapping bits on the remap and offset registers
# show repopulates the gddram in the new correct order
display.rotate(True)
display.show()
sleep(1)

# rotate 0 degrees
display.write_cmd(ssd1327.SET_DISP_OFFSET)  # 0xA2
display.write_cmd(128 - display.height)
display.write_cmd(ssd1327.SET_SEG_REMAP)  # 0xA0
display.write_cmd(0x51)
display.show()
sleep(1)

# rotate 0 degrees (flip horizontal)
display.write_cmd(ssd1327.SET_DISP_OFFSET)  # 0xA2
display.write_cmd(128 - display.height)
display.write_cmd(ssd1327.SET_SEG_REMAP)  # 0xA0
display.write_cmd(0x52)
display.show()
sleep(1)

# rotate 180 degrees
display.write_cmd(ssd1327.SET_DISP_OFFSET)  # 0xA2
display.write_cmd(display.height)
display.write_cmd(ssd1327.SET_SEG_REMAP)  # 0xA0
display.write_cmd(0x42)
display.show()
sleep(1)

# rotate 180 degrees (flip horizontal)
display.write_cmd(ssd1327.SET_DISP_OFFSET)  # 0xA2
display.write_cmd(display.height)
display.write_cmd(ssd1327.SET_SEG_REMAP)  # 0xA0
display.write_cmd(0x41)
display.show()
sleep(1)

# rotate 0 degrees
display.rotate(False)
display.show()
sleep(1)
