from math import pi
from time import sleep_ms

from ism330dl.const import *
from ism330dl.exceptions import *


class ISM330DL(object):
    """MicroPython driver for the ISM330DL 6-axis IMU."""

    def __init__(self, i2c, address=None):
        self.i2c = i2c
        self._buffer_1 = bytearray(1)

        if address is None:
            for addr in (ISM330DL_I2C_ADDR_LOW, ISM330DL_I2C_ADDR_HIGH):
                try:
                    if i2c.readfrom_mem(addr, REG_WHO_AM_I, 1)[0] == ISM330DL_WHO_AM_I_VALUE:
                        address = addr
                        break
                except OSError:
                    pass

            if address is None:
                raise ISM330DLNotFound("ISM330DL not detected on I2C bus")

        self.address = address

        self._accel_scale = ACCEL_FS_2G
        self._gyro_scale = GYRO_FS_250DPS

        self.reset()
        self.configure_accel(ACCEL_ODR_104HZ, ACCEL_FS_2G)
        self.configure_gyro(GYRO_ODR_104HZ, GYRO_FS_250DPS)

    # --------------------------------------------------
    # Low level I2C
    # --------------------------------------------------

    def _read_u8(self, reg):
        self.i2c.readfrom_mem_into(self.address, reg, self._buffer_1)
        return self._buffer_1[0]

    def _write_u8(self, reg, value):
        self._buffer_1[0] = value & 0xFF
        self.i2c.writeto_mem(self.address, reg, self._buffer_1)

    def _read_bytes(self, reg, n):
        return self.i2c.readfrom_mem(self.address, reg, n)

    def _read_i16(self, reg):
        data = self._read_bytes(reg, 2)
        value = data[0] | (data[1] << 8)
        if value & 0x8000:
            value -= 0x10000
        return value

    def _read_vector(self, reg):
        data = self._read_bytes(reg, 6)

        x = data[0] | (data[1] << 8)
        y = data[2] | (data[3] << 8)
        z = data[4] | (data[5] << 8)

        if x & 0x8000:
            x -= 0x10000
        if y & 0x8000:
            y -= 0x10000
        if z & 0x8000:
            z -= 0x10000

        return (x, y, z)

    # --------------------------------------------------
    # Device check
    # --------------------------------------------------

    def who_am_i(self):
        return self._read_u8(REG_WHO_AM_I)

    def check_device(self):
        if self.who_am_i() != ISM330DL_WHO_AM_I_VALUE:
            raise ISM330DLNotFound("ISM330DL not detected")

    # --------------------------------------------------
    # Reset
    # --------------------------------------------------

    def reset(self):
        self._write_u8(REG_CTRL3_C, CTRL3_C_SW_RESET)
        sleep_ms(50)
        self._write_u8(REG_CTRL3_C, CTRL3_C_BDU | CTRL3_C_IF_INC)

    # --------------------------------------------------
    # Configuration
    # --------------------------------------------------

    def configure_accel(self, odr, scale):
        if scale not in ACCEL_FS_BITS:
            raise ISM330DLConfigError("Invalid accel scale")
        self._accel_scale = scale
        value = (odr << 4) | (ACCEL_FS_BITS[scale] << 2)
        self._write_u8(REG_CTRL1_XL, value)

    def configure_gyro(self, odr, scale):
        if scale == GYRO_FS_125DPS:
            value = (odr << 4) | 0x02
        else:
            if scale not in GYRO_FS_BITS:
                raise ISM330DLConfigError("Invalid gyro scale")
            value = (odr << 4) | (GYRO_FS_BITS[scale] << 2)
        self._gyro_scale = scale
        self._write_u8(REG_CTRL2_G, value)

    # --------------------------------------------------
    # Raw readings
    # --------------------------------------------------

    def acceleration_raw(self):
        return self._read_vector(REG_OUTX_L_XL)

    def gyroscope_raw(self):
        return self._read_vector(REG_OUTX_L_G)

    def temperature_raw(self):
        return self._read_i16(REG_OUT_TEMP_L)

    # --------------------------------------------------
    # Converted readings
    # --------------------------------------------------

    def acceleration_g(self):
        sens = ACCEL_SENSITIVITY_MG[self._accel_scale]
        raw = self.acceleration_raw()
        return tuple((v * sens) / 1000.0 for v in raw)

    def acceleration_ms2(self):
        g = self.acceleration_g()
        return tuple(v * STANDARD_GRAVITY for v in g)

    def gyroscope_dps(self):
        sens = GYRO_SENSITIVITY_MDPS[self._gyro_scale]
        raw = self.gyroscope_raw()
        return tuple((v * sens) / 1000.0 for v in raw)

    def gyroscope_rads(self):
        dps = self.gyroscope_dps()
        return tuple(v * pi / 180.0 for v in dps)

    def temperature_c(self):
        raw = self.temperature_raw()
        return TEMP_OFFSET + raw / TEMP_SENSITIVITY

    def orientation(self):
        ax, ay, az = self.acceleration_g()
        threshold = 0.75

        if az > threshold:
            return "SCREEN_DOWN"
        if az < -threshold:
            return "SCREEN_UP"
        if ax > threshold:
            return "TOP_EDGE_DOWN"
        if ax < -threshold:
            return "BOTTOM_EDGE_DOWN"
        if ay > threshold:
            return "RIGHT_EDGE_DOWN"
        if ay < -threshold:
            return "LEFT_EDGE_DOWN"
        return "MOVING"

    def motion(self):
        gx, gy, gz = self.gyroscope_dps()
        threshold = 10

        if abs(gz) > abs(gx) and abs(gz) > abs(gy):
            if gz > threshold:
                return "TURNING RIGHT", gz
            if gz < -threshold:
                return "TURNING LEFT", abs(gz)

        if abs(gx) > abs(gy):
            if gx > threshold:
                return "TILTING LEFT", gx
            if gx < -threshold:
                return "TILTING RIGHT", abs(gx)
        else:
            if gy > threshold:
                return "TILTING DOWN", gy
            if gy < -threshold:
                return "TILTING UP", abs(gy)

        return "STABLE", 0

    # --------------------------------------------------
    # Status
    # --------------------------------------------------

    def status(self):
        s = self._read_u8(REG_STATUS_REG)
        return {
            "temp_ready": bool(s & STATUS_TDA),
            "gyro_ready": bool(s & STATUS_GDA),
            "accel_ready": bool(s & STATUS_XLDA),
        }

    # --------------------------------------------------
    # Power
    # --------------------------------------------------

    def power_down(self):
        self._write_u8(REG_CTRL1_XL, 0)
        self._write_u8(REG_CTRL2_G, 0)
