from micropython import const

# Commands — flash level
CMD_SET_FILENAME = const(0x03)
CMD_GET_FILENAME = const(0x04)
CMD_CLEAR_FLASH = const(0x10)
CMD_WRITE_DATA = const(0x11)
CMD_READ_SECTOR = const(0x20)

# Protocol limits
MAX_WRITE_CHUNK = const(30)
SECTOR_SIZE = const(256)
MAX_SECTORS = const(32768)
FILENAME_LEN = const(8)
EXT_LEN = const(3)
