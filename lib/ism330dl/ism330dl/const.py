# ISM330DL constants


# ---------------------------------------------------------------------
# I2C addresses / identity
# ---------------------------------------------------------------------
ISM330DL_I2C_ADDR_LOW = 0x6A
ISM330DL_I2C_ADDR_HIGH = 0x6B
ISM330DL_WHO_AM_I_VALUE = 0x6A


# ---------------------------------------------------------------------
# Registers
# ---------------------------------------------------------------------
REG_WHO_AM_I = 0x0F
REG_CTRL1_XL = 0x10
REG_CTRL2_G = 0x11
REG_CTRL3_C = 0x12
REG_STATUS_REG = 0x1E

REG_OUT_TEMP_L = 0x20
REG_OUT_TEMP_H = 0x21

REG_OUTX_L_G = 0x22
REG_OUTX_H_G = 0x23
REG_OUTY_L_G = 0x24
REG_OUTY_H_G = 0x25
REG_OUTZ_L_G = 0x26
REG_OUTZ_H_G = 0x27

REG_OUTX_L_XL = 0x28
REG_OUTX_H_XL = 0x29
REG_OUTY_L_XL = 0x2A
REG_OUTY_H_XL = 0x2B
REG_OUTZ_L_XL = 0x2C
REG_OUTZ_H_XL = 0x2D


# ---------------------------------------------------------------------
# CTRL3_C bits
# ---------------------------------------------------------------------
CTRL3_C_BDU = 1 << 6
CTRL3_C_IF_INC = 1 << 2
CTRL3_C_SW_RESET = 1 << 0


# ---------------------------------------------------------------------
# STATUS bits
# ---------------------------------------------------------------------
STATUS_TDA = 1 << 2
STATUS_GDA = 1 << 1
STATUS_XLDA = 1 << 0


# ---------------------------------------------------------------------
# Accelerometer ODR
# ---------------------------------------------------------------------
ACCEL_ODR_POWER_DOWN = 0x00
ACCEL_ODR_12_5HZ = 0x01
ACCEL_ODR_26HZ = 0x02
ACCEL_ODR_52HZ = 0x03
ACCEL_ODR_104HZ = 0x04
ACCEL_ODR_208HZ = 0x05
ACCEL_ODR_416HZ = 0x06
ACCEL_ODR_833HZ = 0x07
ACCEL_ODR_1660HZ = 0x08


# ---------------------------------------------------------------------
# Accelerometer full scale
# ---------------------------------------------------------------------
ACCEL_FS_2G = 2
ACCEL_FS_4G = 4
ACCEL_FS_8G = 8
ACCEL_FS_16G = 16

ACCEL_FS_BITS = {
    ACCEL_FS_2G: 0x00,
    ACCEL_FS_16G: 0x01,
    ACCEL_FS_4G: 0x02,
    ACCEL_FS_8G: 0x03,
}

ACCEL_SENSITIVITY_MG = {
    ACCEL_FS_2G: 0.061,
    ACCEL_FS_4G: 0.122,
    ACCEL_FS_8G: 0.244,
    ACCEL_FS_16G: 0.488,
}


# ---------------------------------------------------------------------
# Gyroscope ODR
# ---------------------------------------------------------------------
GYRO_ODR_POWER_DOWN = 0x00
GYRO_ODR_12_5HZ = 0x01
GYRO_ODR_26HZ = 0x02
GYRO_ODR_52HZ = 0x03
GYRO_ODR_104HZ = 0x04
GYRO_ODR_208HZ = 0x05
GYRO_ODR_416HZ = 0x06
GYRO_ODR_833HZ = 0x07
GYRO_ODR_1660HZ = 0x08


# ---------------------------------------------------------------------
# Gyroscope full scale
# ---------------------------------------------------------------------
GYRO_FS_125DPS = 125
GYRO_FS_250DPS = 250
GYRO_FS_500DPS = 500
GYRO_FS_1000DPS = 1000
GYRO_FS_2000DPS = 2000

GYRO_FS_BITS = {
    GYRO_FS_250DPS: 0x00,
    GYRO_FS_500DPS: 0x01,
    GYRO_FS_1000DPS: 0x02,
    GYRO_FS_2000DPS: 0x03,
}

GYRO_SENSITIVITY_MDPS = {
    GYRO_FS_125DPS: 4.375,
    GYRO_FS_250DPS: 8.75,
    GYRO_FS_500DPS: 17.50,
    GYRO_FS_1000DPS: 35.0,
    GYRO_FS_2000DPS: 70.0,
}


TEMP_SENSITIVITY = 256.0
TEMP_OFFSET = 25.0

STANDARD_GRAVITY = 9.80665
