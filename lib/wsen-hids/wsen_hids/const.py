"""
Constants for the WSEN-HIDS 2525020210001 humidity and temperature sensor.
"""

WSEN_HIDS_I2C_ADDRESS = 0x5F
WSEN_HIDS_DEVICE_ID = 0xBC

# Register map
REG_DEVICE_ID = 0x0F
REG_AV_CONF = 0x10
REG_CTRL_1 = 0x20
REG_CTRL_2 = 0x21
REG_CTRL_3 = 0x22
REG_STATUS = 0x27
REG_H_OUT_L = 0x28
REG_H_OUT_H = 0x29
REG_T_OUT_L = 0x2A
REG_T_OUT_H = 0x2B

# Calibration registers
REG_H0_RH_X2 = 0x30
REG_H1_RH_X2 = 0x31
REG_T0_DEGC_X8 = 0x32
REG_T1_DEGC_X8 = 0x33
REG_T1_T0_MSB = 0x35
REG_H0_T0_OUT_L = 0x36
REG_H0_T0_OUT_H = 0x37
REG_H1_T0_OUT_L = 0x3A
REG_H1_T0_OUT_H = 0x3B
REG_T0_OUT_L = 0x3C
REG_T0_OUT_H = 0x3D
REG_T1_OUT_L = 0x3E
REG_T1_OUT_H = 0x3F

# Multi-byte read auto increment for I2C
AUTO_INCREMENT = 0x80

# CTRL_1 bits
CTRL_1_PD = 1 << 7
CTRL_1_BDU = 1 << 2
CTRL_1_ODR_MASK = 0x03

# Output data rate values
ODR_ONE_SHOT = 0x00
ODR_1_HZ = 0x01
ODR_7_HZ = 0x02
ODR_12_5_HZ = 0x03

# CTRL_2 bits
CTRL_2_BOOT = 1 << 7
CTRL_2_HEATER = 1 << 3
CTRL_2_ONE_SHOT = 1 << 0

# CTRL_3 bits
CTRL_3_DRDY_H_L = 1 << 7
CTRL_3_PP_OD = 1 << 6
CTRL_3_DRDY_EN = 1 << 2

# STATUS bits
STATUS_H_DA = 1 << 1
STATUS_T_DA = 1 << 0

# Average register masks
AVG_T_MASK = 0x38
AVG_H_MASK = 0x07

# Average presets
AVG_2 = 0x00
AVG_4 = 0x01
AVG_8 = 0x02
AVG_16 = 0x03
AVG_32 = 0x04
AVG_64 = 0x05
AVG_128 = 0x06
AVG_256 = 0x07

# Default averaging according to the manual:
# temperature = 16 samples, humidity = 32 samples
AVG_T_DEFAULT = AVG_16
AVG_H_DEFAULT = AVG_16  # value 0x03 => 32 samples for humidity

DEFAULT_ONE_SHOT_TIMEOUT_MS = 100
DEFAULT_BOOT_TIME_MS = 10
