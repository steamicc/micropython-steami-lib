from micropython import const

# commands
SET_COL_ADDR = const(0x15)
SET_SCROLL_DEACTIVATE = const(0x2E)
SET_ROW_ADDR = const(0x75)
SET_CONTRAST = const(0x81)
SET_SEG_REMAP = const(0xA0)
SET_DISP_START_LINE = const(0xA1)
SET_DISP_OFFSET = const(0xA2)
SET_DISP_MODE = const(0xA4)  # 0xA4 normal, 0xA5 all on, 0xA6 all off, 0xA7 when inverted
SET_MUX_RATIO = const(0xA8)
SET_FN_SELECT_A = const(0xAB)
SET_DISP = const(0xAE)  # 0xAE power off, 0xAF power on
SET_PHASE_LEN = const(0xB1)
SET_DISP_CLK_DIV = const(0xB3)
SET_SECOND_PRECHARGE = const(0xB6)
SET_GRAYSCALE_TABLE = const(0xB8)
SET_GRAYSCALE_LINEAR = const(0xB9)
SET_PRECHARGE = const(0xBC)
SET_VCOM_DESEL = const(0xBE)
SET_FN_SELECT_B = const(0xD5)
SET_COMMAND_LOCK = const(0xFD)

# registers
REG_CMD = const(0x80)
REG_DATA = const(0x40)
