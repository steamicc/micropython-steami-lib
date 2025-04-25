from ssd1327.const import *
from time import sleep_us

import framebuf


class SSD1327:
    def __init__(self, width=128, height=128):
        self.width = width
        self.height = height
        self.buffer = bytearray(self.width * self.height // 2)
        self.framebuf = framebuf.FrameBuffer(
            self.buffer, self.width, self.height, framebuf.GS4_HMSB
        )

        self.col_addr = ((128 - self.width) // 4, 63 - ((128 - self.width) // 4))
        # 96x96     (8, 55)
        # 128x128   (0, 63)

        self.row_addr = (0, self.height - 1)
        # 96x96     (0, 95)
        # 128x128   (0, 127)

        self.offset = 128 - self.height
        # 96x96     32
        # 128x128   0

        self.poweron()
        self.init_display()

    def init_display(self):
        for cmd in (
            SET_COMMAND_LOCK,
            0x12,  # Unlock
            SET_DISP,  # Display off
            # Resolution and layout
            SET_DISP_START_LINE,
            0x00,
            SET_DISP_OFFSET,
            self.offset,  # Set vertical offset by COM from 0~127
            # Set re-map
            # Enable column address re-map
            # Disable nibble re-map
            # Horizontal address increment
            # Enable COM re-map
            # Enable COM split odd even
            SET_SEG_REMAP,
            0x51,
            SET_MUX_RATIO,
            self.height - 1,
            # Timing and driving scheme
            SET_FN_SELECT_A,
            0x01,  # Enable internal VDD regulator
            SET_PHASE_LEN,
            0x51,  # Phase 1: 1 DCLK, Phase 2: 5 DCLKs
            SET_DISP_CLK_DIV,
            0x01,  # Divide ratio: 1, Oscillator Frequency: 0
            SET_PRECHARGE,
            0x08,  # Set pre-charge voltage level: VCOMH
            SET_VCOM_DESEL,
            0x07,  # Set VCOMH COM deselect voltage level: 0.86*Vcc
            SET_SECOND_PRECHARGE,
            0x01,  # Second Pre-charge period: 1 DCLK
            SET_FN_SELECT_B,
            0x62,  # Enable enternal VSL, Enable second precharge
            # Display
            SET_GRAYSCALE_LINEAR,  # Use linear greyscale lookup table
            SET_CONTRAST,
            0x7F,  # Medium brightness
            SET_DISP_MODE,  # Normal, not inverted
            SET_COL_ADDR,
            self.col_addr[0],
            self.col_addr[1],
            SET_ROW_ADDR,
            self.row_addr[0],
            self.row_addr[1],
            SET_SCROLL_DEACTIVATE,
            SET_DISP | 0x01,
        ):  # Display on
            self.write_cmd(cmd)
        self.fill(0)
        self.write_data(self.buffer)

    def poweroff(self):
        self.write_cmd(SET_FN_SELECT_A)
        self.write_cmd(0x00)  # Disable internal VDD regulator, to save power
        self.write_cmd(SET_DISP)

    def poweron(self):
        self.write_cmd(SET_FN_SELECT_A)
        self.write_cmd(0x01)  # Enable internal VDD regulator
        self.write_cmd(SET_DISP | 0x01)

    def contrast(self, contrast):
        self.write_cmd(SET_CONTRAST)
        self.write_cmd(contrast)  # 0-255

    def rotate(self, rotate):
        self.poweroff()
        self.write_cmd(SET_DISP_OFFSET)
        self.write_cmd(self.height if rotate else self.offset)
        self.write_cmd(SET_SEG_REMAP)
        self.write_cmd(0x42 if rotate else 0x51)
        self.poweron()

    def invert(self, invert):
        self.write_cmd(
            SET_DISP_MODE | (invert & 1) << 1 | (invert & 1)
        )  # 0xA4=Normal, 0xA7=Inverted

    def show(self):
        self.write_cmd(SET_COL_ADDR)
        self.write_cmd(self.col_addr[0])
        self.write_cmd(self.col_addr[1])
        self.write_cmd(SET_ROW_ADDR)
        self.write_cmd(self.row_addr[0])
        self.write_cmd(self.row_addr[1])
        self.write_data(self.buffer)

    def lookup(self, data):
        pass

    def fill(self, col):
        self.framebuf.fill(col)

    def pixel(self, x, y, col):
        self.framebuf.pixel(x, y, col)

    def line(self, x1, y1, x2, y2, col):
        self.framebuf.line(x1, y1, x2, y2, col)

    def scroll(self, dx, dy):
        self.framebuf.scroll(dx, dy)
        # software scroll

    def text(self, string, x, y, col=15):
        self.framebuf.text(string, x, y, col)

    def write_cmd(self):
        raise NotImplementedError

    def write_data(self):
        raise NotImplementedError


class SSD1327_I2C(SSD1327):
    def __init__(self, width, height, i2c, addr=0x3C):
        self.i2c = i2c
        self.addr = addr
        self.cmd_arr = bytearray([REG_CMD, 0])  # Co=1, D/C#=0
        self.data_list = [bytes((REG_DATA,)), None]
        super().__init__(width, height)

    def write_cmd(self, cmd):
        self.cmd_arr[1] = cmd
        self.i2c.writeto(self.addr, self.cmd_arr)

    def write_data(self, data_buf):
        self.data_list[1] = data_buf
        self.i2c.writevto(self.addr, self.data_list)


class SSD1327_SPI(SSD1327):
    def __init__(self, width, height, spi, dc, res, cs):
        self.rate = 10000000
        dc.init(dc.OUT, value=0)
        res.init(res.OUT, value=1)
        cs.init(cs.OUT, value=1)
        print(dc, res, cs)
        self.spi = spi
        self.dc = dc
        self.res = res
        self.cs = cs
        self.reset()
        super().__init__(width, height)

    def reset(self):
        self.res.value(False)
        sleep_us(500)
        self.res.value(True)

    def write_cmd(self, cmd):
        self.spi.init(baudrate=self.rate, polarity=0, phase=0)
        self.cs.value(True)
        self.dc.value(False)
        self.cs.value(False)
        self.spi.write(bytearray([cmd]))
        self.cs.value(True)

    def write_data(self, buf):
        self.spi.init(baudrate=self.rate, polarity=0, phase=0)
        self.cs.value(True)
        self.dc.value(True)
        self.cs.value(False)
        self.spi.write(buf)
        self.cs.value(True)


class WS_OLED_128X128_SPI(SSD1327_SPI):
    def __init__(self, spi, dc, res, cs):
        super().__init__(128, 128, spi, dc, res, cs)


class WS_OLED_128X128_I2C(SSD1327_I2C):
    def __init__(self, i2c, addr=0x3C):
        super().__init__(128, 128, i2c, addr)
