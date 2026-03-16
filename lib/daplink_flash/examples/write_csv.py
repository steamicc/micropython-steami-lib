"""Write CSV data to flash via DAPLink bridge."""

from machine import I2C
from time import sleep_ms
from daplink_flash import DaplinkFlash

i2c = I2C(1)
flash = DaplinkFlash(i2c)

print("WHO_AM_I:", hex(flash.device_id()))

# Set filename and erase
flash.set_filename("DATA", "CSV")
flash.clear_flash()
sleep_ms(500)
print("Flash erased.")

# Write CSV header + data
flash.write_line("temperature;humidity;pressure")
flash.write_line("25.3;48.2;1013.5")
flash.write_line("25.5;47.8;1013.4")
flash.write_line("25.4;48.0;1013.6")
print("Data written.")

# Read back
content = flash.read()
print("File content:")
print(content.decode())
