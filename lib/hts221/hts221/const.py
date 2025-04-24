from micropython import const

# HTS221 I2C address
HTS_I2C_ADDR = const(0x5F)

# HTS221 register mapping
HTS221_WHO_AM_I = const(0x0F)
HTS221_AV_CONF = const(0x10)
HTS221_CTRL_REG1 = const(0x20)
HTS221_CTRL_REG2 = const(0x21)
HTS221_CTRL_REG3 = const(0x22)
HTS221_STATUS_REG = const(0x27)
HTS221_HUMIDITY_OUT_L = const(0x28)
HTS221_HUMIDITY_OUT_H = const(0x29)
HTS221_TEMP_OUT_L = const(0x2A)
HTS221_TEMP_OUT_H = const(0x2B)
HTS221_H0_rH_x2 = const(0x30)
HTS221_H1_rH_x2 = const(0x31)
HTS221_T0_degC_x8 = const(0x32)
HTS221_T1_degC_x8 = const(0x33)
HTS221_T1T0_msb = const(0x35)
HTS221_H0_T0_OUT_L = const(0x36)
HTS221_H0_T0_OUT_H = const(0x37)
HTS221_H1_T0_OUT_L = const(0x3A)
HTS221_H1_T0_OUT_H = const(0x3B)
HTS221_T0_OUT_L = const(0x3C)
HTS221_T0_OUT_H = const(0x3D)
HTS221_T1_OUT_L = const(0x3E)
HTS221_T1_OUT_H = const(0x3F)
