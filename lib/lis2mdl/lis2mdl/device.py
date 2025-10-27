# device.py
# This driver is for the LIS2MDL magnetometer sensor. It provides methods for initialization, calibration, and reading magnetic field data.

from machine import I2C
from lis2mdl.const import *
import time
import math

class LIS2MDL(object):
    # Default calibration offsets and scales for the magnetometer
    x_off = -132.0
    y_off = -521.5
    z_off = -891.0

    x_scale = 273.0
    y_scale = 313.5
    z_scale = 295.0

    def __init__(self, i2c, address=LIS2MDL_I2C_ADDR, odr_hz=10, temp_comp=True, low_power=False, drdy_pin=False):
        # Initialize the LIS2MDL sensor with the given I2C interface and settings.
        self.i2c = i2c
        self.address = address
        self.writebuffer = bytearray(1)
        self.readbuffer = bytearray(1)

        # Perform a soft reset to ensure the sensor starts in a known state.
        self.setReg(0x20, LIS2MDL_CFG_REG_A)  # SOFT_RST=1 (not 0x10)
        try:
            import time; time.sleep_ms(10)  # Small delay for reset to complete
        except:
            pass

        # Configure the sensor's operating mode, output data rate, and other settings.
        odr_bits = {10:0b00, 20:0b01, 50:0b10, 100:0b11}.get(odr_hz, 0b00)
        comp = 1 if temp_comp else 0
        lp   = 1 if low_power else 0
        cfg_a = (comp<<7) | (lp<<4) | (odr_bits<<2) | 0b00
        self.setReg(cfg_a, LIS2MDL_CFG_REG_A)   # Essential to exit IDLE mode

        # Configure low-pass filter and other optional settings.
        self.setReg(0x00, LIS2MDL_CFG_REG_B)  # Default: LPF and offset cancellation off

        # Enable block data update and optionally configure the DRDY pin.
        cfg_c = 0x10 | (0x01 if drdy_pin else 0x00)
        self.setReg(cfg_c, LIS2MDL_CFG_REG_C)

    # --- Low-level I2C communication methods ---
    def setReg(self, data, reg):
        # Write a byte to a specific register.
        self.writebuffer[0] = data
        self.i2c.writeto_mem(self.address, reg, self.writebuffer)

    def getReg(self, reg):
        # Read a byte from a specific register.
        self.i2c.readfrom_mem_into(self.address, reg, self.readbuffer)
        return self.readbuffer[0]

    @staticmethod
    def _to_int16(v):
        # Convert an unsigned 16-bit value to a signed 16-bit value.
        return v - 0x10000 if v & 0x8000 else v

    def read_magnet(self):
        # Read the raw magnetic field data (X, Y, Z) from the sensor.
        buf = self.i2c.readfrom_mem(self.address, LIS2MDL_OUTX_L_REG | 0x80, 6)
        x = self._to_int16((buf[1] << 8) | buf[0])
        y = self._to_int16((buf[3] << 8) | buf[2])
        z = self._to_int16((buf[5] << 8) | buf[4])
        return (x, y, z)

    def whoAmI(self):
        # Return the WHO_AM_I register value to verify the sensor's identity.
        return self.getReg(LIS2MDL_WHO_AM_I)

    def status(self):
        # Return the STATUS_REG value to check the sensor's status.
        return self.getReg(LIS2MDL_STATUS_REG)

    def set_calibrate_step(self, xoff, yoff, zoff, xscale, yscale, zscale):
        # Set the calibration offsets and scales manually.
        self.x_off = xoff
        self.y_off = yoff
        self.z_off = zoff
        self.x_scale = xscale
        self.y_scale = yscale
        self.z_scale = zscale

    def calibrate_step(self):
        # Perform a quick 3D calibration by rotating the board flat over 360°.
        print("Quick 3D calibration: rotate the board FLAT over 360°...")
        
        xmin = ymin = zmin =  1e9
        xmax = ymax = zmax = -1e9

        for _ in range(150):
            x, y, z = self.read_magnet()
            xmin = min(xmin, x); xmax = max(xmax, x)
            ymin = min(ymin, y); ymax = max(ymax, y)
            zmin = min(zmin, z); zmax = max(zmax, z)
            time.sleep_ms(20)
        
        # Calculate offsets and scales based on the min/max values.
        self.x_off = (xmax + xmin) / 2.0
        self.y_off = (ymax + ymin) / 2.0
        self.z_off = (zmax + zmin) / 2.0

        self.x_scale = (xmax - xmin) / 2.0
        self.y_scale = (ymax - ymin) / 2.0
        self.z_scale = (zmax - zmin) / 2.0

    def get_calibration(self):
        # Return the current calibration offsets and scales.
        return (self.x_off, self.y_off, self.z_off, self.x_scale, self.y_scale, self.z_scale)
    
    def heading_flat_only(self):
        # Calculate the heading (angle) assuming the sensor is flat.
        x, y, z = self.read_magnet()
        x = (x - self.x_off) / self.x_scale
        y = (y - self.y_off) / self.y_scale
        angle = math.degrees(math.atan2(x, y))
        if angle < 0:
            angle += 360
        return angle
    
    def heading_with_tilt_compensation(self, read_accel):
        # Calculate the heading with tilt compensation using accelerometer data.
        # Note: This method has not been tested as no accelerometer was available during development.

        # Read magnetometer and accelerometer data.
        x, y, z = self.read_magnet()
        ax, ay, az = read_accel()

        # Apply 3D calibration (offsets and scales for each axis).
        x = (x - self.x_off) / self.x_scale
        y = (y - self.y_off) / self.y_scale
        z = (z - self.z_off) / self.z_scale

        # Calculate roll and pitch from accelerometer data.
        roll  = math.atan2(ay, az)
        pitch = math.atan2(-ax, math.sqrt(ay*ay + az*az))

        # Adjust the magnetic vector to account for tilt.
        Xh = x * math.cos(pitch) + z * math.sin(pitch)
        Yh = x * math.sin(roll) * math.sin(pitch) + y * math.cos(roll) - z * math.sin(roll) * math.cos(pitch)

        # Calculate the heading (0 to 360°).
        angle = math.degrees(math.atan2(Xh, Yh))
        if angle < 0:
            angle += 360
        return angle

    def direction_label(self, angle):
        # Return a compass direction label (e.g., N, NE, E, etc.) based on the angle.
        dirs = ["N","NE","E","SE","S","SW","W","NW","N"]
        idx = int((angle + 22.5)//45)
        return dirs[idx]