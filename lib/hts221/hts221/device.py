from machine import I2C
from time import sleep_ms

from hts221.const import *


def int16(d):
    return d if d < 0x8000 else d - 0x10000


class HTS221(object):
    def __init__(self, i2c, address=HTS_I2C_ADDR):
        self.i2c = i2c
        self.address = address

        self.writebuffer = bytearray(1)
        self.readbuffer = bytearray(1)

        self._temp_gain = 1.0
        self._temp_offset = 0.0

        self._read_temperature_calibration()
        self._read_humidity_calibration()

        # set av conf: T=4 H=8
        self.set_av(0x81)
        # set CTRL_REG1: PD=1 BDU=1 ODR=1
        self.set_odr(0x85)

    def _read_temperature_calibration(self):
        # HTS221 Temp Calibration registers
        self.T0_OUT = int16(self._read_reg16(HTS221_T0_OUT_L))
        self.T1_OUT = int16(self._read_reg16(HTS221_T1_OUT_L))

        t1 = self._read_reg(HTS221_T1T0_msb)
        self.T0_degC = (self._read_reg(HTS221_T0_degC_x8) + (t1 % 4) * 256) / 8
        self.T1_degC = (self._read_reg(HTS221_T1_degC_x8) + ((t1 % 16) / 4) * 256) / 8

    def _read_humidity_calibration(self):
        # HTS221 Humi Calibration registers
        self.H0_OUT = self._read_reg16(HTS221_H0_T0_OUT_L)
        self.H1_OUT = self._read_reg16(HTS221_H1_T0_OUT_L)
        self.H0_rH = self._read_reg(HTS221_H0_rH_x2) / 2
        self.H1_rH = self._read_reg(HTS221_H1_rH_x2) / 2

    def _write_reg(self, reg, dat):
        self.writebuffer[0] = dat
        self.i2c.writeto_mem(self.address, reg, self.writebuffer)

    def _read_reg(self, reg):
        self.i2c.readfrom_mem_into(self.address, reg, self.readbuffer)
        return self.readbuffer[0]

    def _read_reg16(self, reg):
        lo = self._read_reg(reg)
        hi = self._read_reg(reg + 1)
        return (hi << 8) + lo

    # Device identification
    def device_id(self):
        return self._read_reg(HTS221_WHO_AM_I)

    # get STATUS register
    def _status(self):
        return self._read_reg(HTS221_STATUS_REG)

    def data_ready(self):
        s = self._status()
        return bool((s & HTS221_STATUS_T_DA) and (s & HTS221_STATUS_H_DA))

    def temperature_ready(self):
        return bool(self._status() & HTS221_STATUS_T_DA)

    def humidity_ready(self):
        return bool(self._status() & HTS221_STATUS_H_DA)

    # power control
    def power_off(self):
        t = self._read_reg(HTS221_CTRL_REG1) & 0x7F
        self._write_reg(HTS221_CTRL_REG1, t)

    def power_on(self):
        t = self._read_reg(HTS221_CTRL_REG1) | 0x80
        self._write_reg(HTS221_CTRL_REG1, t)

    # get/set Output data rate
    def get_odr(self):
        return self._read_reg(HTS221_CTRL_REG1) & 0x03

    def set_odr(self, odr=0):
        t = self._read_reg(HTS221_CTRL_REG1) & 0xFC
        self._write_reg(HTS221_CTRL_REG1, t | odr)

    # get/set Humidity and temperature average configuration
    def get_av(self):
        return self._read_reg(HTS221_AV_CONF)

    def set_av(self, av=0):
        self._write_reg(HTS221_AV_CONF, av)

    # one-shot / auto-trigger helpers
    def _is_power_down(self):
        return (self._read_reg(HTS221_CTRL_REG1) & HTS221_CTRL1_PD) == 0

    def _is_one_shot_mode(self):
        ctrl1 = self._read_reg(HTS221_CTRL_REG1)
        is_active = bool(ctrl1 & HTS221_CTRL1_PD)
        odr = ctrl1 & HTS221_CTRL1_ODR_MASK
        return is_active and odr == 0

    def trigger_one_shot(self):
        ctrl1 = self._read_reg(HTS221_CTRL_REG1)
        ctrl1 |= HTS221_CTRL1_PD | HTS221_CTRL1_BDU
        ctrl1 &= ~HTS221_CTRL1_ODR_MASK
        self._write_reg(HTS221_CTRL_REG1, ctrl1)
        ctrl2 = self._read_reg(HTS221_CTRL_REG2)
        self._write_reg(HTS221_CTRL_REG2, ctrl2 | HTS221_CTRL2_ONE_SHOT)
        sleep_ms(15)

    def reboot(self):
        ctrl2 = self._read_reg(HTS221_CTRL_REG2)
        self._write_reg(HTS221_CTRL_REG2, ctrl2 | HTS221_CTRL2_BOOT)
        sleep_ms(15)
        self._read_temperature_calibration()
        self._read_humidity_calibration()

    def _ensure_data(self):
        if self._is_power_down() or self._is_one_shot_mode():
            self.trigger_one_shot()
            ready_mask = HTS221_STATUS_T_DA | HTS221_STATUS_H_DA
            for _ in range(50):
                if (self._read_reg(HTS221_STATUS_REG) & ready_mask) == ready_mask:
                    return
                sleep_ms(2)
            raise OSError("HTS221 data ready timeout")

    # calculate Temperature
    def temperature(self):
        self._ensure_data()
        t = self._read_reg16(HTS221_TEMP_OUT_L)
        factory = self.T0_degC + (self.T1_degC - self.T0_degC) * (t - self.T0_OUT) / (
            self.T1_OUT - self.T0_OUT
        )
        return self._temp_gain * factory + self._temp_offset

    # calculate Humidity
    def humidity(self):
        self._ensure_data()
        t = self._read_reg16(HTS221_HUMIDITY_OUT_L)
        return self.H0_rH + (self.H1_rH - self.H0_rH) * (t - self.H0_OUT) / (
            self.H1_OUT - self.H0_OUT
        )

    # get Humidity and Temperature
    def read(self):
        self._ensure_data()
        h = self._read_reg16(HTS221_HUMIDITY_OUT_L)
        t = self._read_reg16(HTS221_TEMP_OUT_L)
        humidity = self.H0_rH + (self.H1_rH - self.H0_rH) * (h - self.H0_OUT) / (
            self.H1_OUT - self.H0_OUT
        )
        factory = self.T0_degC + (self.T1_degC - self.T0_degC) * (t - self.T0_OUT) / (
            self.T1_OUT - self.T0_OUT
        )
        temperature = self._temp_gain * factory + self._temp_offset
        return humidity, temperature

    # Temperature calibration

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
        delta = float(measured_high - measured_low)
        if delta == 0.0:
            raise ValueError("measured_low and measured_high must differ")
        self._temp_gain = float(ref_high - ref_low) / delta
        self._temp_offset = float(ref_low) - self._temp_gain * float(measured_low)
