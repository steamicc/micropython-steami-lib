from micropython import const

# I2C address (7-bit) — 0x76 in 8-bit (CODAL convention)
DAPLINK_FLASH_DEFAULT_ADDR = const(0x3B)

# WHO_AM_I expected value
DAPLINK_FLASH_WHO_AM_I_VAL = const(0x4C)

# Commands
CMD_WHO_AM_I = const(0x01)
CMD_SET_FILENAME = const(0x03)
CMD_GET_FILENAME = const(0x04)
CMD_CLEAR_FLASH = const(0x10)
CMD_WRITE_DATA = const(0x11)
CMD_READ_SECTOR = const(0x20)

# Registers
REG_STATUS = const(0x80)
REG_ERROR = const(0x81)

# Status register bits
STATUS_BUSY = const(0x80)

# Error register bits
ERROR_BAD_PARAM = const(0x01)
ERROR_FILE_FULL = const(0x20)
ERROR_BAD_FILENAME = const(0x40)
ERROR_CMD_FAILED = const(0x80)

# Protocol limits
MAX_WRITE_CHUNK = const(30)
SECTOR_SIZE = const(256)
FILENAME_LEN = const(8)
EXT_LEN = const(3)
