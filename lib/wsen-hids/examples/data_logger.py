'''
Read every 5s and print CSV-formatted output (timestamp, humidity, temperature) suitable for serial capture
This example writes data both to the serial console and to DAPLink flash storage.

WARNING: If configured to erase on startup, this script will erase the entire
DAPLink flash contents before logging, which is a destructive operation.
Make sure you have backed up any important data before enabling erasure.
'''
from time import sleep_ms, ticks_diff, ticks_ms

from daplink_flash import DaplinkFlash
from machine import I2C
from wsen_hids import WSEN_HIDS

i2c = I2C(1)
sensor = WSEN_HIDS(i2c)
flash = DaplinkFlash(i2c)

# Set filename and erase
flash.set_filename("data", "CSV")
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
