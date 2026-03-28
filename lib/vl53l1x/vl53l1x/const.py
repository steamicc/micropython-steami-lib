from micropython import const

# I2C address
VL53L1X_I2C_DEFAULT_ADDR = const(0x29)

# Device identification
REG_MODEL_ID = const(0x010F)
VL53L1X_DEVICE_ID = const(0xEACC)

# System control
REG_SOFT_RESET = const(0x0000)
SOFT_RESET_ASSERT = const(0x00)
SOFT_RESET_RELEASE = const(0x01)

# Default configuration start register
REG_DEFAULT_CONFIG_START = const(0x2D)

# Timing
REG_RESULT_OSC_CALIBRATE_VAL = const(0x0022)
REG_RANGE_CONFIG_VCSEL_PERIOD_A = const(0x001E)

# Ranging control
REG_SYSTEM_START = const(0x0087)
RANGING_START = const(0x40)
RANGING_STOP = const(0x00)

# Interrupt
REG_GPIO_HV_MUX_CTRL = const(0x0030)
GPIO_HV_MUX_CTRL_POLARITY = const(0x10)
REG_GPIO_TIO_HV_STATUS = const(0x0031)
GPIO_TIO_HV_STATUS_DATA_READY = const(0x01)
REG_SYSTEM_INTERRUPT_CLEAR = const(0x0086)
INTERRUPT_CLEAR = const(0x01)

# Result registers
REG_RESULT_RANGE_STATUS = const(0x0089)
RESULT_BLOCK_SIZE = const(17)
RESULT_DISTANCE_MSB_OFFSET = const(13)
RESULT_DISTANCE_LSB_OFFSET = const(14)
