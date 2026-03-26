"""Log humidity and temperature to DAPLink flash and serial console.

Reads every 5 seconds and writes CSV-formatted output (timestamp,
humidity, temperature).  Data is stored on the DAPLink flash as
DATA.CSV and also printed to the serial console.

WARNING: When ERASE_FLASH_ON_START is True, the entire DAPLink flash
is erased before logging.  Make sure you have backed up any important
data before enabling erasure.
"""
from time import sleep_ms, ticks_diff, ticks_ms

from daplink_flash import DaplinkFlash
from machine import I2C
from wsen_hids import WSEN_HIDS

# Set to True to erase the DAPLink flash on startup (DESTRUCTIVE).
ERASE_FLASH_ON_START = False

i2c = I2C(1)
sensor = WSEN_HIDS(i2c)
flash = DaplinkFlash(i2c)

flash.set_filename("DATA", "CSV")
if ERASE_FLASH_ON_START:
    flash.clear_flash()
    sleep_ms(500)
    print("Flash erased.")

start_ms = ticks_ms()

print("timestamp,humidity,temperature")
flash.write_line("timestamp,humidity,temperature")

while True:
    humidity, temperature = sensor.read_one_shot()
    elapsed_s = ticks_diff(ticks_ms(), start_ms) // 1000

    print("{},{:.2f},{:.2f}".format(elapsed_s, humidity, temperature))
    flash.write_line("{},{:.2f},{:.2f}".format(elapsed_s, humidity, temperature))

    sleep_ms(5000)
