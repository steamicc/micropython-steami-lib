from micropython import const

# I2C address (7-bit) — 0x76 in 8-bit (CODAL convention)
DAPLINK_BRIDGE_DEFAULT_ADDR = const(0x3B)

# WHO_AM_I expected value
DAPLINK_BRIDGE_WHO_AM_I_VAL = const(0x4C)

# Commands — bridge level
CMD_WHO_AM_I = const(0x01)
CMD_WRITE_CONFIG = const(0x30)
CMD_READ_CONFIG = const(0x31)
CMD_CLEAR_CONFIG = const(0x32)

# Registers
REG_STATUS = const(0x80)
REG_ERROR = const(0x81)

# Status register bits
STATUS_BUSY = const(0x80)

# Error register bits
ERROR_BAD_PARAM = const(0x01)
ERROR_CMD_FAILED = const(0x80)

# Protocol limits
MAX_WRITE_CHUNK = const(30)
SECTOR_SIZE = const(256)
CONFIG_SIZE = const(1024)
