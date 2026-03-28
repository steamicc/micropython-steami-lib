"""Erase all data from the flash memory."""

from time import sleep_ms

from daplink_bridge import DaplinkBridge
from daplink_flash import DaplinkFlash
from machine import I2C

i2c = I2C(1)
bridge = DaplinkBridge(i2c)
flash = DaplinkFlash(bridge)

name, ext = flash.get_filename()
print("Current file: {}.{}".format(name, ext))

print("Erasing flash...")
flash.clear_flash()
sleep_ms(1000)

print("Done. Flash is empty.")
print("ERROR: 0x{:02X}".format(bridge._error()))
