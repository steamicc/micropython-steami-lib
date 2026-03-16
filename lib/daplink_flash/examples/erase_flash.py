"""Erase all data from the flash memory."""

from machine import I2C
from time import sleep_ms
from daplink_flash import DaplinkFlash

i2c = I2C(1)
flash = DaplinkFlash(i2c)

name, ext = flash.get_filename()
print("Current file: {}.{}".format(name, ext))

print("Erasing flash...")
flash.clear_flash()
sleep_ms(1000)

print("Done. Flash is empty.")
print("ERROR: 0x{:02X}".format(flash._error()))
