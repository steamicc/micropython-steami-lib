from machine import I2C
from lis2mdl.const import *

class LIS2MDL(object):
    def __init__(self, i2c, address=LIS2MDL_I2C_ADDR):
        self.i2c = i2c
        self.address = address

        self.writebuffer = bytearray(1)
        self.readbuffer = bytearray(1)

        # Initialize the device
        self.reset()
        self.configure()

    def reset(self):
        # Reset the device using CFG_REG_A
        self.setReg(0x10, LIS2MDL_CFG_REG_A)

    def configure(self):
        # Configure the device (example: enable continuous mode)
        self.setReg(0x00, LIS2MDL_CFG_REG_B)
        self.setReg(0x01, LIS2MDL_CFG_REG_C)

    def setReg(self, data, reg):
        self.writebuffer[0] = data
        self.i2c.writeto_mem(self.address, reg, self.writebuffer)

    def getReg(self, reg):
        self.i2c.readfrom_mem_into(self.address, reg, self.readbuffer)
        return self.readbuffer[0]

    def get2Reg(self, reg):
        lowerByte = self.getReg(reg)
        higherByte = self.getReg(reg + 1)
        return (higherByte << 8) + lowerByte

    def read_magnet(self):
        # Read magnetic field data for X, Y, Z axes
        x = self.get2Reg(LIS2MDL_OUTX_L_REG)
        y = self.get2Reg(LIS2MDL_OUTY_L_REG)
        z = self.get2Reg(LIS2MDL_OUTZ_L_REG)
        return (x, y, z)

    def whoAmI(self):
        # Read the WHO_AM_I register
        return self.getReg(LIS2MDL_WHO_AM_I)

    def status(self):
        # Read the STATUS register
        return self.getReg(LIS2MDL_STATUS_REG)