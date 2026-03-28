"""Display DAPLink Flash bridge status and filename."""

from daplink_bridge import DaplinkBridge
from daplink_flash import DaplinkFlash
from machine import I2C

i2c = I2C(1)
bridge = DaplinkBridge(i2c)
flash = DaplinkFlash(bridge)

print("=== DAPLink Flash Info ===")
print("WHO_AM_I: 0x{:02X}".format(bridge.device_id()))
print("STATUS:   0x{:02X}".format(bridge._status()))
print("ERROR:    0x{:02X}".format(bridge._error()))
print("Busy:    ", bridge.busy())

name, ext = flash.get_filename()
print("Filename: {}.{}".format(name, ext))
