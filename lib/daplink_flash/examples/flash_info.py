"""Display DAPLink Flash bridge status and filename."""

from machine import I2C
from daplink_flash import DaplinkFlash

i2c = I2C(1)
flash = DaplinkFlash(i2c)

print("=== DAPLink Flash Info ===")
print("WHO_AM_I: 0x{:02X}".format(flash.device_id()))
print("STATUS:   0x{:02X}".format(flash._status()))
print("ERROR:    0x{:02X}".format(flash._error()))
print("Busy:    ", flash.busy())

name, ext = flash.get_filename()
print("Filename: {}.{}".format(name, ext))
