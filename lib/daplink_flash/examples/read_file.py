"""Read and display the current file stored on flash."""

from daplink_bridge import DaplinkBridge
from daplink_flash import DaplinkFlash
from machine import I2C

i2c = I2C(1)
bridge = DaplinkBridge(i2c)
flash = DaplinkFlash(bridge)

name, ext = flash.get_filename()
print("Reading file: {}.{}".format(name, ext))
print()

content = flash.read()
if len(content) == 0:
    print("(empty)")
else:
    print(content.decode())
    print("---")
    print("{} bytes".format(len(content)))
