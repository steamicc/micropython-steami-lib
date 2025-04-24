from machine import I2C

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
        self.T0_OUT = int16(self.get2Reg(HTS221_T0_OUT_L))
        self.T1_OUT = int16(self.get2Reg(HTS221_T1_OUT_L))

        t1 = self.getReg(HTS221_T1T0_msb)
        self.T0_degC = (self.getReg(HTS221_T0_degC_x8) + (t1 % 4) * 256) / 8
        self.T1_degC = (self.getReg(HTS221_T1_degC_x8) + ((t1 % 16) / 4) * 256) / 8

    def calibrate_humidity(self):
        # HTS221 Humi Calibration registers
        self.H0_OUT = self.get2Reg(HTS221_H0_T0_OUT_L)
        self.H1_OUT = self.get2Reg(HTS221_H1_T0_OUT_L)
        self.H0_rH = self.getReg(HTS221_H0_rH_x2) / 2
        self.H1_rH = self.getReg(HTS221_H1_rH_x2) / 2

    def setReg(self, dat, reg):
        self.writebuffer[0] = dat
        self.i2c.writeto_mem(self.address, reg, self.writebuffer)

    def getReg(self, reg):
        self.i2c.readfrom_mem_into(self.address, reg, self.readbuffer)
        return self.readbuffer[0]

    def get2Reg(self, reg):
        lowerByte = self.getReg(reg)
        higherByte = self.getReg(reg + 1)
        return (higherByte << 8) + lowerByte

    # Device identification
    def whoAmI(self):
        return self.getReg(HTS221_WHO_AM_I)

    # get STATUS register
    def status(self):
        return self.getReg(HTS221_STATUS_REG)

    # power control
    def poweroff(self):
        t = self.getReg(HTS221_CTRL_REG1) & 0x7F
        self.setReg(t, HTS221_CTRL_REG1)

    def poweron(self):
        t = self.getReg(HTS221_CTRL_REG1) | 0x80
        self.setReg(t, HTS221_CTRL_REG1)

    # get/set Output data rate
    def getODR(self):
        return self.getReg(HTS221_CTRL_REG1) & 0x03

    def setODR(self, odr=0):
        t = self.getReg(HTS221_CTRL_REG1) & 0xFC
        self.setReg(t | odr, HTS221_CTRL_REG1)

    # get/set Humidity and temperature average configuration
    def getAv():
        return self.getReg(HTS221_AV_CONF)

    def setAv(self, av=0):
        self.setReg(av, HTS221_AV_CONF)

    # calculate Temperature
    def temperature(self):
        t = self.get2Reg(HTS221_TEMP_OUT_L)
        return self.T0_degC + (self.T1_degC - self.T0_degC) * (t - self.T0_OUT) / (
            self.T1_OUT - self.T0_OUT
        )

    # calculate Humidity
    def humidity(self):
        t = self.get2Reg(HTS221_HUMIDITY_OUT_L)
        return self.H0_rH + (self.H1_rH - self.H0_rH) * (t - self.H0_OUT) / (
            self.H1_OUT - self.H0_OUT
        )

    # get Humidity and Temperature
    def get(self):
        return [self.humidity(), self.temperature()]
