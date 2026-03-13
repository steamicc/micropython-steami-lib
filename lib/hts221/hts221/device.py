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

        self.calibrate_temperature()
        self.calibrate_humidity()

        # set av conf: T=4 H=8
        self.setAv(0x81)
        # set CTRL_REG1: PD=1 BDU=1 ODR=1
        self.setODR(0x85)

    def calibrate_temperature(self):
        # HTS221 Temp Calibration registers
        self.T0_OUT = int16(self._read_reg16(HTS221_T0_OUT_L))
        self.T1_OUT = int16(self._read_reg16(HTS221_T1_OUT_L))

        t1 = self._read_reg(HTS221_T1T0_msb)
        self.T0_degC = (self._read_reg(HTS221_T0_degC_x8) + (t1 % 4) * 256) / 8
        self.T1_degC = (self._read_reg(HTS221_T1_degC_x8) + ((t1 % 16) / 4) * 256) / 8

    def calibrate_humidity(self):
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
        lowerByte = self._read_reg(reg)
        higherByte = self._read_reg(reg + 1)
        return (higherByte << 8) + lowerByte

    # Device identification
    def whoAmI(self):
        return self._read_reg(HTS221_WHO_AM_I)

    # get STATUS register
    def status(self):
        return self._read_reg(HTS221_STATUS_REG)

    # power control
    def poweroff(self):
        t = self._read_reg(HTS221_CTRL_REG1) & 0x7F
        self._write_reg(HTS221_CTRL_REG1, t)

    def poweron(self):
        t = self._read_reg(HTS221_CTRL_REG1) | 0x80
        self._write_reg(HTS221_CTRL_REG1, t)

    # get/set Output data rate
    def getODR(self):
        return self._read_reg(HTS221_CTRL_REG1) & 0x03

    def setODR(self, odr=0):
        t = self._read_reg(HTS221_CTRL_REG1) & 0xFC
        self._write_reg(HTS221_CTRL_REG1, t | odr)

    # get/set Humidity and temperature average configuration
    def getAv(self):
        return self._read_reg(HTS221_AV_CONF)

    def setAv(self, av=0):
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

    def _ensure_data(self):
        if self._is_power_down() or self._is_one_shot_mode():
            self.trigger_one_shot()

    # calculate Temperature
    def temperature(self):
        self._ensure_data()
        t = self._read_reg16(HTS221_TEMP_OUT_L)
        return self.T0_degC + (self.T1_degC - self.T0_degC) * (t - self.T0_OUT) / (
            self.T1_OUT - self.T0_OUT
        )

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
        temperature = self.T0_degC + (self.T1_degC - self.T0_degC) * (t - self.T0_OUT) / (
            self.T1_OUT - self.T0_OUT
        )
        return humidity, temperature

    def get(self):
        h, t = self.read()
        return [h, t]
