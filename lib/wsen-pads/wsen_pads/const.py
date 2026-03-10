"""
Constants for the WSEN-PADS pressure and temperature sensor.

All register addresses and bit definitions in this file come from the
official WSEN-PADS user manual.
"""

# ============================================================================
# I2C addressing
# ============================================================================

# 7-bit I2C address when SAO pin is tied low
WSEN_PADS_I2C_ADDR_SAO_LOW = 0x5C

# 7-bit I2C address when SAO pin is tied high
WSEN_PADS_I2C_ADDR_SAO_HIGH = 0x5D

# Default address recommended for a single device on the bus
WSEN_PADS_I2C_DEFAULT_ADDR = WSEN_PADS_I2C_ADDR_SAO_HIGH

# Expected device ID value
WSEN_PADS_DEVICE_ID = 0xB3

# ============================================================================
# Register map
# ============================================================================

REG_INT_CFG = 0x0B
REG_THR_P_L = 0x0C
REG_THR_P_H = 0x0D
REG_INTERFACE_CTRL = 0x0E
REG_DEVICE_ID = 0x0F
REG_CTRL_1 = 0x10
REG_CTRL_2 = 0x11
REG_CTRL_3 = 0x12
REG_FIFO_CTRL = 0x13
REG_FIFO_WTM = 0x14
REG_REF_P_L = 0x15
REG_REF_P_H = 0x16
REG_OPC_P_L = 0x18
REG_OPC_P_H = 0x19
REG_INT_SOURCE = 0x24
REG_FIFO_STATUS_1 = 0x25
REG_FIFO_STATUS_2 = 0x26
REG_STATUS = 0x27
REG_DATA_P_XL = 0x28
REG_DATA_P_L = 0x29
REG_DATA_P_H = 0x2A
REG_DATA_T_L = 0x2B
REG_DATA_T_H = 0x2C

# FIFO output registers (not used yet in the V1 driver)
REG_FIFO_DATA_P_XL = 0x78
REG_FIFO_DATA_P_L = 0x79
REG_FIFO_DATA_P_H = 0x7A
REG_FIFO_DATA_T_L = 0x7B
REG_FIFO_DATA_T_H = 0x7C

# ============================================================================
# CTRL_1 register bits
# ============================================================================

# ODR[2:0] field occupies bits 6:4
CTRL1_ODR_SHIFT = 4
CTRL1_ODR_MASK = 0x70

# Enable second low-pass filter for pressure
CTRL1_EN_LPFP = 1 << 3

# Low-pass filter bandwidth configuration
CTRL1_LPFP_CFG = 1 << 2

# Block data update
CTRL1_BDU = 1 << 1

# SPI mode selection (not used in I2C mode)
CTRL1_SIM = 1 << 0

# ============================================================================
# CTRL_2 register bits
# ============================================================================

CTRL2_BOOT = 1 << 7
CTRL2_INT_H_L = 1 << 6
CTRL2_PP_OD = 1 << 5
CTRL2_IF_ADD_INC = 1 << 4
CTRL2_SWRESET = 1 << 2
CTRL2_LOW_NOISE_EN = 1 << 1
CTRL2_ONE_SHOT = 1 << 0

# ============================================================================
# INT_SOURCE register bits
# ============================================================================

INT_SOURCE_BOOT_ON = 1 << 7
INT_SOURCE_IA = 1 << 2
INT_SOURCE_PL = 1 << 1
INT_SOURCE_PH = 1 << 0

# ============================================================================
# STATUS register bits
# ============================================================================

STATUS_T_OR = 1 << 5
STATUS_P_OR = 1 << 4
STATUS_T_DA = 1 << 1
STATUS_P_DA = 1 << 0

# ============================================================================
# Output data rate (ODR) values for CTRL_1[6:4]
# ============================================================================

ODR_POWER_DOWN = 0x00
ODR_1_HZ = 0x01
ODR_10_HZ = 0x02
ODR_25_HZ = 0x03
ODR_50_HZ = 0x04
ODR_75_HZ = 0x05
ODR_100_HZ = 0x06
ODR_200_HZ = 0x07

# ============================================================================
# Conversion constants
# ============================================================================

# Pressure sensitivity:
# 1 digit = 1 / 40960 kPa = 1 / 4096 hPa = 1 / 40.96 Pa
PRESSURE_HPA_PER_DIGIT = 1.0 / 4096.0
PRESSURE_KPA_PER_DIGIT = 1.0 / 40960.0
PRESSURE_PA_PER_DIGIT = 1.0 / 40.96

# Temperature sensitivity:
# 1 digit = 0.01 °C
TEMPERATURE_C_PER_DIGIT = 0.01

# ============================================================================
# Timing helpers
# ============================================================================

# Typical boot time after power-up is up to 4.5 ms, so 5 ms is a safe minimum.
BOOT_DELAY_MS = 5

# Typical conversion time in one-shot mode
ONE_SHOT_LOW_POWER_DELAY_MS = 5
ONE_SHOT_LOW_NOISE_DELAY_MS = 15
