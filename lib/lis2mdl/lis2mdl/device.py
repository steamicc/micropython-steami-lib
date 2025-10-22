# device.py
from machine import I2C
from lis2mdl.const import *

class LIS2MDL(object):
    def __init__(self, i2c, address=LIS2MDL_I2C_ADDR, odr_hz=10, temp_comp=True, low_power=False, drdy_pin=False):
        self.i2c = i2c
        self.address = address
        self.writebuffer = bytearray(1)
        self.readbuffer = bytearray(1)

        # Soft reset property
        self.setReg(0x20, LIS2MDL_CFG_REG_A)  # SOFT_RST=1 (not 0x10)
        # small delay (if needed on the MicroPython side)
        try:
            import time; time.sleep_ms(10)
        except:
            pass

        # CFG_REG_A: COMP_TEMP, LP, ODR, MD=00 (continuous)
        odr_bits = {10:0b00, 20:0b01, 50:0b10, 100:0b11}.get(odr_hz, 0b00)
        comp = 1 if temp_comp else 0
        lp   = 1 if low_power else 0
        cfg_a = (comp<<7) | (lp<<4) | (odr_bits<<2) | 0b00
        self.setReg(cfg_a, LIS2MDL_CFG_REG_A)   # <- essential to exit IDLE

        # CFG_REG_B: default 0x00 (LPF/off_canc off); you can enable LPF if desired
        self.setReg(0x00, LIS2MDL_CFG_REG_B)

        # CFG_REG_C: BDU=1 (+ DRDY_on_PIN if requested)
        cfg_c = 0x10 | (0x01 if drdy_pin else 0x00)
        self.setReg(cfg_c, LIS2MDL_CFG_REG_C)

    # --- identical low-level ---
    def setReg(self, data, reg):
        self.writebuffer[0] = data
        self.i2c.writeto_mem(self.address, reg, self.writebuffer)

    def getReg(self, reg):
        self.i2c.readfrom_mem_into(self.address, reg, self.readbuffer)
        return self.readbuffer[0]

    # signed helper
    @staticmethod
    def _to_int16(v):
        return v - 0x10000 if v & 0x8000 else v

    # burst read + signed
    def read_magnet(self):
        # auto-increment: reg | 0x80 (cf. datasheet I2C op)
        buf = self.i2c.readfrom_mem(self.address, LIS2MDL_OUTX_L_REG | 0x80, 6)
        x = self._to_int16((buf[1] << 8) | buf[0])
        y = self._to_int16((buf[3] << 8) | buf[2])
        z = self._to_int16((buf[5] << 8) | buf[4])
        return (x, y, z)

    def whoAmI(self):
        return self.getReg(LIS2MDL_WHO_AM_I)

    def status(self):
        return self.getReg(LIS2MDL_STATUS_REG)
