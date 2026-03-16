"""Read and display the current file stored on flash."""

from machine import I2C
from daplink_flash import DaplinkFlash

i2c = I2C(1)
flash = DaplinkFlash(i2c)

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
