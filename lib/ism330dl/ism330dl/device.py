from math import pi
from time import sleep_ms

from ism330dl.const import *
from ism330dl.exceptions import *


class ISM330DL(object):
    """MicroPython driver for the ISM330DL 6-axis IMU."""

    def __init__(self, i2c, address=ISM330DL_I2C_DEFAULT_ADDR):
        self.i2c = i2c
        self.address = address
        self._buffer_1 = bytearray(1)

        self._accel_scale = ACCEL_FS_2G
        self._accel_odr = ACCEL_ODR_104HZ
        self._gyro_scale = GYRO_FS_250DPS
        self._gyro_odr = GYRO_ODR_104HZ

        self._temp_gain = 1.0
        self._temp_offset = 0.0

        self.check_device()
        self.soft_reset()
        self.configure_accel(ACCEL_ODR_104HZ, ACCEL_FS_2G)
        self.configure_gyro(GYRO_ODR_104HZ, GYRO_FS_250DPS)

    # --------------------------------------------------
    # Low level I2C
    # --------------------------------------------------

    def _read_u8(self, reg):
        try:
            self.i2c.readfrom_mem_into(self.address, reg, self._buffer_1)
        except OSError as exc:
            raise ISM330DLIOError("Read register 0x{:02X}".format(reg)) from exc
        return self._buffer_1[0]

    def _write_u8(self, reg, value):
        try:
            self._buffer_1[0] = value & 0xFF
            self.i2c.writeto_mem(self.address, reg, self._buffer_1)
        except OSError as exc:
            raise ISM330DLIOError("Write register 0x{:02X}".format(reg)) from exc

    def _read_bytes(self, reg, n):
        try:
            return self.i2c.readfrom_mem(self.address, reg, n)
        except OSError as exc:
            raise ISM330DLIOError("Read {} bytes from 0x{:02X}".format(n, reg)) from exc

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

    def device_id(self):
        return self._read_u8(REG_WHO_AM_I)

    def check_device(self):
        if self.device_id() != ISM330DL_WHO_AM_I_VALUE:
            raise ISM330DLNotFound("ISM330DL not detected")

    # --------------------------------------------------
    # Soft reset
    # --------------------------------------------------

    def soft_reset(self):
        self._write_u8(REG_CTRL3_C, CTRL3_C_SW_RESET)
        sleep_ms(50)
        self._write_u8(REG_CTRL3_C, CTRL3_C_BDU | CTRL3_C_IF_INC)

    # --------------------------------------------------
    # Configuration
    # --------------------------------------------------

    def configure_accel(self, odr, scale):
        if odr not in ACCEL_ODR_VALUES:
            raise ISM330DLConfigError("Invalid accel ODR")
        if scale not in ACCEL_FS_BITS:
            raise ISM330DLConfigError("Invalid accel scale")
        self._accel_scale = scale
        if odr != ACCEL_ODR_POWER_DOWN:
            self._accel_odr = odr
        value = (odr << 4) | (ACCEL_FS_BITS[scale] << 2)
        self._write_u8(REG_CTRL1_XL, value)

    def configure_gyro(self, odr, scale):
        if odr not in GYRO_ODR_VALUES:
            raise ISM330DLConfigError("Invalid gyro ODR")
        if scale == GYRO_FS_125DPS:
            value = (odr << 4) | 0x02
        else:
            if scale not in GYRO_FS_BITS:
                raise ISM330DLConfigError("Invalid gyro scale")
            value = (odr << 4) | (GYRO_FS_BITS[scale] << 2)
        self._gyro_scale = scale
        if odr != GYRO_ODR_POWER_DOWN:
            self._gyro_odr = odr
        self._write_u8(REG_CTRL2_G, value)

    # --------------------------------------------------
    # Auto-trigger
    # --------------------------------------------------

    def _is_power_down(self):
        """Return True if both accel and gyro ODR are 0 (power-down)."""
        ctrl1 = self._read_u8(REG_CTRL1_XL)
        ctrl2 = self._read_u8(REG_CTRL2_G)
        return (ctrl1 & 0xF0) == 0 and (ctrl2 & 0xF0) == 0

    def _ensure_data(self):
        """Restore previous ODR and wait for data if in power-down mode."""
        if self._is_power_down():
            self.configure_accel(self._accel_odr, self._accel_scale)
            self.configure_gyro(self._gyro_odr, self._gyro_scale)
            ready_mask = STATUS_XLDA | STATUS_GDA | STATUS_TDA
            for _ in range(50):
                if (self._read_u8(REG_STATUS_REG) & ready_mask) == ready_mask:
                    return
                sleep_ms(10)
            raise OSError("ISM330DL data ready timeout")

    # --------------------------------------------------
    # Raw readings
    # --------------------------------------------------

    def acceleration_raw(self):
        self._ensure_data()
        return self._read_vector(REG_OUTX_L_XL)

    def gyroscope_raw(self):
        self._ensure_data()
        return self._read_vector(REG_OUTX_L_G)

    def temperature_raw(self):
        self._ensure_data()
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
        factory = TEMP_OFFSET + self.temperature_raw() / TEMP_SENSITIVITY
        return self._temp_gain * factory + self._temp_offset

    def set_temp_offset(self, offset_c):
        """Set a temperature offset in °C (gain remains 1.0)."""
        self._temp_gain = 1.0
        self._temp_offset = float(offset_c)

    def calibrate_temperature(self, ref_low, measured_low, ref_high, measured_high):
        """Two-point calibration from reference measurements.

        Args:
            ref_low: reference temperature at the low point (°C).
            measured_low: sensor reading at the low point (°C).
            ref_high: reference temperature at the high point (°C).
            measured_high: sensor reading at the high point (°C).
        """
        delta = float(measured_high - measured_low)
        if delta == 0.0:
            raise ValueError("measured_low and measured_high must differ")
        self._temp_gain = float(ref_high - ref_low) / delta
        self._temp_offset = float(ref_low) - self._temp_gain * float(measured_low)

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

    def power_off(self):
        self._write_u8(REG_CTRL1_XL, 0)
        self._write_u8(REG_CTRL2_G, 0)

    def power_on(self):
        self.configure_accel(self._accel_odr, self._accel_scale)
        self.configure_gyro(self._gyro_odr, self._gyro_scale)
