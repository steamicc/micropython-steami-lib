from micropython import const

# I2C addresses
BME280_I2C_ADDR_LOW = const(0x76)   # SDO → GND
BME280_I2C_ADDR_HIGH = const(0x77)  # SDO → VDDIO
BME280_I2C_DEFAULT_ADDR = const(0x76)

# Device identification
REG_CHIP_ID = const(0xD0)
BME280_CHIP_ID = const(0x60)

# Reset
REG_SOFT_RESET = const(0xE0)
SOFT_RESET_CMD = const(0xB6)

# Status
REG_STATUS = const(0xF3)
STATUS_MEASURING = const(0x08)
STATUS_IM_UPDATE = const(0x01)

# Control registers
REG_CTRL_HUM = const(0xF2)
REG_CTRL_MEAS = const(0xF4)
REG_CONFIG = const(0xF5)

# Data registers (burst read 0xF7-0xFE = 8 bytes)
REG_DATA_START = const(0xF7)
DATA_BLOCK_SIZE = const(8)

# Calibration data registers
REG_CALIB_TEMP_PRESS = const(0x88)  # 26 bytes: T1..T3, P1..P9, _, H1
CALIB_TP_SIZE = const(26)
REG_CALIB_HUM = const(0xE1)         # 7 bytes: H2..H6
CALIB_H_SIZE = const(7)

# Measurement modes
MODE_SLEEP = const(0x00)
MODE_FORCED = const(0x01)
MODE_NORMAL = const(0x03)
MODE_MASK = const(0x03)

# Oversampling
OSRS_SKIP = const(0x00)
OSRS_X1 = const(0x01)
OSRS_X2 = const(0x02)
OSRS_X4 = const(0x03)
OSRS_X8 = const(0x04)
OSRS_X16 = const(0x05)

# ctrl_meas bit positions
OSRS_T_SHIFT = const(5)
OSRS_P_SHIFT = const(2)

# IIR filter coefficients (config register bits 4:2)
FILTER_OFF = const(0x00)
FILTER_2 = const(0x01)
FILTER_4 = const(0x02)
FILTER_8 = const(0x03)
FILTER_16 = const(0x04)
FILTER_SHIFT = const(2)

# Standby time (config register bits 7:5)
STANDBY_0_5_MS = const(0x00)
STANDBY_62_5_MS = const(0x01)
STANDBY_125_MS = const(0x02)
STANDBY_250_MS = const(0x03)
STANDBY_500_MS = const(0x04)
STANDBY_1000_MS = const(0x05)
STANDBY_SHIFT = const(5)

# Timing
BOOT_DELAY_MS = const(10)
RESET_DELAY_MS = const(10)
