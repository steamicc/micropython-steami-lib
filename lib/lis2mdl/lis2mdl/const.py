from micropython import const

# LIS2MDL I2C address
LIS2MDL_I2C_ADDR = const(0x1E)

# Register addresses
LIS2MDL_WHO_AM_I = const(0x4F)  # Device identification register
LIS2MDL_CFG_REG_A = const(0x60)  # Configuration register A
LIS2MDL_CFG_REG_B = const(0x61)  # Configuration register B
LIS2MDL_CFG_REG_C = const(0x62)  # Configuration register C
LIS2MDL_STATUS_REG = const(0x67)  # Status register

# Output data registers
LIS2MDL_OUTX_L_REG = const(0x68)  # X-axis output low byte
LIS2MDL_OUTX_H_REG = const(0x69)  # X-axis output high byte
LIS2MDL_OUTY_L_REG = const(0x6A)  # Y-axis output low byte
LIS2MDL_OUTY_H_REG = const(0x6B)  # Y-axis output high byte
LIS2MDL_OUTZ_L_REG = const(0x6C)  # Z-axis output low byte
LIS2MDL_OUTZ_H_REG = const(0x6D)  # Z-axis output high byte

# Offset registers
LIS2MDL_OFFSET_X_REG_L = const(0x45)  # X-axis offset low byte
LIS2MDL_OFFSET_X_REG_H = const(0x46)  # X-axis offset high byte
LIS2MDL_OFFSET_Y_REG_L = const(0x47)  # Y-axis offset low byte
LIS2MDL_OFFSET_Y_REG_H = const(0x48)  # Y-axis offset high byte
LIS2MDL_OFFSET_Z_REG_L = const(0x49)  # Z-axis offset low byte
LIS2MDL_OFFSET_Z_REG_H = const(0x4A)  # Z-axis offset high byte