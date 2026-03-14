from time import sleep_ms, ticks_ms, ticks_diff

from .const import *
from .exceptions import (
    WSENHIDSError,
    WSENHIDSCommunicationError,
    WSENHIDSDeviceIDError,
    WSENHIDSTimeoutError,
)


class WSEN_HIDS(object):
    """
    MicroPython driver for the WSEN-HIDS 2525020210001.

    Public API:
        - read()
        - humidity()
        - temperature()
        - read_one_shot()
        - set_continuous_mode()
        - set_one_shot_mode()
        - enable_bdu()
        - enable_heater()
        - set_average()
        - status()
        - data_ready()
    """

    ODR_ONE_SHOT = ODR_ONE_SHOT
    ODR_1_HZ = ODR_1_HZ
    ODR_7_HZ = ODR_7_HZ
    ODR_12_5_HZ = ODR_12_5_HZ

    AVG_2 = AVG_2
    AVG_4 = AVG_4
    AVG_8 = AVG_8
    AVG_16 = AVG_16
    AVG_32 = AVG_32
    AVG_64 = AVG_64
    AVG_128 = AVG_128
    AVG_256 = AVG_256

    DEFAULT_ONE_SHOT_TIMEOUT_MS = 100
    DEFAULT_BOOT_TIME_MS = 10

    def __init__(
        self,
        i2c,
        address=WSEN_HIDS_I2C_ADDRESS,
        check_device=True,
        enable_bdu=True,
        avg_t=AVG_T_DEFAULT,
        avg_h=AVG_H_DEFAULT,
    ):
        self.i2c = i2c
        self.address = address

        self._buffer_1 = bytearray(1)

        self._calibration = {}
        self._temp_gain = 1.0
        self._temp_offset = 0.0

        if check_device:
            self.check_device()

        self.set_average(avg_t, avg_h)

        if enable_bdu:
            self.enable_bdu(True)

        self._read_calibration()

    # -------------------------------------------------------------------------
    # Low-level helpers
    # -------------------------------------------------------------------------

    def _read_reg(self, reg):
        try:
            self.i2c.readfrom_mem_into(self.address, reg, self._buffer_1)
            return self._buffer_1[0]
        except OSError as exc:
            raise WSENHIDSCommunicationError("Unable to read register 0x{:02X}".format(reg)) from exc

    def _write_reg(self, reg, value):
        try:
            self._buffer_1[0] = value & 0xFF
            self.i2c.writeto_mem(self.address, reg, self._buffer_1)
        except OSError as exc:
            raise WSENHIDSCommunicationError("Unable to write register 0x{:02X}".format(reg)) from exc

    def _read_regs(self, reg, length):
        try:
            if length > 1:
                reg |= AUTO_INCREMENT
            return self.i2c.readfrom_mem(self.address, reg, length)
        except OSError as exc:
            raise WSENHIDSCommunicationError(
                "Unable to read {} bytes from register 0x{:02X}".format(length, reg)
            ) from exc

    def _update_reg(self, reg, mask, value):
        current = self._read_reg(reg)
        current &= ~mask
        current |= (value & mask)
        self._write_reg(reg, current)

    def _read_u16_le(self, reg_l):
        data = self._read_regs(reg_l, 2)
        return data[0] | (data[1] << 8)

    def _read_s16_le(self, reg_l):
        value = self._read_u16_le(reg_l)
        if value & 0x8000:
            value -= 0x10000
        return value

    @staticmethod
    def _clamp(value, minimum, maximum):
        if value < minimum:
            return minimum
        if value > maximum:
            return maximum
        return value

    # -------------------------------------------------------------------------
    # Identification / calibration
    # -------------------------------------------------------------------------

    def device_id(self):
        return self._read_reg(REG_DEVICE_ID)

    def check_device(self):
        device_id = self.device_id()
        if device_id != WSEN_HIDS_DEVICE_ID:
            raise WSENHIDSDeviceIDError(
                "Invalid device ID 0x{:02X}, expected 0x{:02X}".format(
                    device_id, WSEN_HIDS_DEVICE_ID
                )
            )
        return True

    def _read_calibration(self):
        h0_rh_x2 = self._read_reg(REG_H0_RH_X2)
        h1_rh_x2 = self._read_reg(REG_H1_RH_X2)
        t0_degC_x8_lsb = self._read_reg(REG_T0_DEGC_X8)
        t1_degC_x8_lsb = self._read_reg(REG_T1_DEGC_X8)
        t1_t0_msb = self._read_reg(REG_T1_T0_MSB)

        t0_degC_x8 = ((t1_t0_msb & 0x03) << 8) | t0_degC_x8_lsb
        t1_degC_x8 = ((t1_t0_msb & 0x0C) << 6) | t1_degC_x8_lsb

        self._calibration = {
            "H0_rH": h0_rh_x2 / 2.0,
            "H1_rH": h1_rh_x2 / 2.0,
            "H0_T0_OUT": self._read_s16_le(REG_H0_T0_OUT_L),
            "H1_T0_OUT": self._read_s16_le(REG_H1_T0_OUT_L),
            "T0_degC": t0_degC_x8 / 8.0,
            "T1_degC": t1_degC_x8 / 8.0,
            "T0_OUT": self._read_s16_le(REG_T0_OUT_L),
            "T1_OUT": self._read_s16_le(REG_T1_OUT_L),
        }

    # -------------------------------------------------------------------------
    # Configuration
    # -------------------------------------------------------------------------

    def enable_bdu(self, enabled=True):
        value = CTRL_1_BDU if enabled else 0
        self._update_reg(REG_CTRL_1, CTRL_1_BDU, value)

    def set_average(self, avg_t=AVG_T_DEFAULT, avg_h=AVG_H_DEFAULT):
        avg_t &= 0x07
        avg_h &= 0x07
        value = (avg_t << 3) | avg_h
        self._write_reg(REG_AV_CONF, value)

    def set_one_shot_mode(self):
        ctrl1 = self._read_reg(REG_CTRL_1)
        ctrl1 |= CTRL_1_PD          # sensor active
        ctrl1 &= ~CTRL_1_ODR_MASK   # ODR = 00 => one-shot
        self._write_reg(REG_CTRL_1, ctrl1)

    def set_continuous_mode(self, odr=ODR_1_HZ):
        if odr not in (ODR_1_HZ, ODR_7_HZ, ODR_12_5_HZ):
            raise ValueError("Invalid ODR for continuous mode")

        ctrl1 = self._read_reg(REG_CTRL_1)
        ctrl1 |= CTRL_1_PD
        ctrl1 &= ~CTRL_1_ODR_MASK
        ctrl1 |= odr
        self._write_reg(REG_CTRL_1, ctrl1)

    def enable_heater(self, enabled=True):
        value = CTRL_2_HEATER if enabled else 0
        self._update_reg(REG_CTRL_2, CTRL_2_HEATER, value)

    def reboot_memory(self):
        self._update_reg(REG_CTRL_2, CTRL_2_BOOT, CTRL_2_BOOT)
        sleep_ms(self.DEFAULT_BOOT_TIME_MS)
        self._read_calibration()

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------

    def status(self):
        return self._read_reg(REG_STATUS)

    def humidity_ready(self):
        return bool(self.status() & STATUS_H_DA)

    def temperature_ready(self):
        return bool(self.status() & STATUS_T_DA)

    def data_ready(self):
        status = self.status()
        return bool((status & STATUS_H_DA) and (status & STATUS_T_DA))

    # -------------------------------------------------------------------------
    # Raw reads / conversions
    # -------------------------------------------------------------------------

    def _read_raw_humidity_temperature(self):
        # Multi-byte read with auto-increment bit set.
        data = self._read_regs(REG_H_OUT_L, 4)

        h_raw = data[0] | (data[1] << 8)
        t_raw = data[2] | (data[3] << 8)

        if h_raw & 0x8000:
            h_raw -= 0x10000
        if t_raw & 0x8000:
            t_raw -= 0x10000

        return h_raw, t_raw

    def _convert_humidity(self, h_raw):
        h0_rh = self._calibration["H0_rH"]
        h1_rh = self._calibration["H1_rH"]
        h0_out = self._calibration["H0_T0_OUT"]
        h1_out = self._calibration["H1_T0_OUT"]

        delta_out = h1_out - h0_out
        if delta_out == 0:
            raise WSENHIDSError("Invalid humidity calibration data")

        humidity = ((h1_rh - h0_rh) * (h_raw - h0_out) / delta_out) + h0_rh
        return self._clamp(humidity, 0.0, 100.0)

    def _convert_temperature(self, t_raw):
        t0_degC = self._calibration["T0_degC"]
        t1_degC = self._calibration["T1_degC"]
        t0_out = self._calibration["T0_OUT"]
        t1_out = self._calibration["T1_OUT"]

        delta_out = t1_out - t0_out
        if delta_out == 0:
            raise WSENHIDSError("Invalid temperature calibration data")

        factory = ((t1_degC - t0_degC) * (t_raw - t0_out) / delta_out) + t0_degC
        return self._temp_gain * factory + self._temp_offset

    # -------------------------------------------------------------------------
    # Calibration
    # -------------------------------------------------------------------------

    def set_temp_offset(self, offset_c):
        """Set a temperature offset in °C (gain remains 1.0).

        Args:
            offset_c: offset value in degrees Celsius.
        """
        self._temp_gain = 1.0
        self._temp_offset = float(offset_c)

    def calibrate_temperature(self, ref_low, measured_low, ref_high, measured_high):
        """Two-point calibration from reference measurements.

        Computes gain and offset so that the sensor reading is adjusted
        to match reference values at two temperature points.

        Args:
            ref_low: reference temperature at the low point (°C).
            measured_low: sensor reading at the low point (°C).
            ref_high: reference temperature at the high point (°C).
            measured_high: sensor reading at the high point (°C).
        """
        self._temp_gain = float(ref_high - ref_low) / float(measured_high - measured_low)
        self._temp_offset = float(ref_low) - self._temp_gain * float(measured_low)

    # -------------------------------------------------------------------------
    # Public measurement API
    # -------------------------------------------------------------------------

    def _is_power_down(self):
        ctrl1 = self._read_reg(REG_CTRL_1)
        return (ctrl1 & CTRL_1_PD) == 0

    def _ensure_data(self, timeout_ms=DEFAULT_ONE_SHOT_TIMEOUT_MS):
        if not self._is_power_down():
            return

        self.trigger_one_shot()

        start = ticks_ms()
        while not self.data_ready():
            if ticks_diff(ticks_ms(), start) >= timeout_ms:
                raise WSENHIDSTimeoutError("One-shot measurement timeout")
            sleep_ms(1)

    def read(self):
        self._ensure_data()

        h_raw, t_raw = self._read_raw_humidity_temperature()
        humidity = self._convert_humidity(h_raw)
        temperature = self._convert_temperature(t_raw)
        return humidity, temperature

    def humidity(self):
        return self.read()[0]

    def temperature(self):
        return self.read()[1]

    def trigger_one_shot(self):
        self.set_one_shot_mode()
        self._update_reg(REG_CTRL_2, CTRL_2_ONE_SHOT, CTRL_2_ONE_SHOT)

    def read_one_shot(self, timeout_ms=DEFAULT_ONE_SHOT_TIMEOUT_MS):
        self.trigger_one_shot()

        start = ticks_ms()
        while not self.data_ready():
            if ticks_diff(ticks_ms(), start) >= timeout_ms:
                raise WSENHIDSTimeoutError("One-shot measurement timeout")
            sleep_ms(1)

        return self.read()
