"""
Log magnetic field X, Y, Z and temperature to DAPLink flash as CSV every second for 60 seconds.
Uses daplink_flash (set_filename, write_line).
File is then accessible via USB mass storage for analysis in a spreadsheet.
"""

from time import sleep_ms, ticks_diff, ticks_ms

from daplink_bridge import DaplinkBridge
from daplink_flash import DaplinkFlash
from lis2mdl import LIS2MDL
from machine import I2C

# Set to True to erase the DAPLink flash on startup (DESTRUCTIVE).
ERASE_FLASH_ON_START = False

LOG_DURATION_S = 60
SAMPLE_PERIOD_MS = 1000


i2c = I2C(1)
sensor = LIS2MDL(i2c)
bridge = DaplinkBridge(i2c)
flash = DaplinkFlash(bridge)

flash.set_filename("LIS2MDL", "CSV")
if ERASE_FLASH_ON_START:
    flash.clear_flash()
    sleep_ms(500)
    print("Flash erased.")

start_ms = ticks_ms()

header = "timestamp_s,x_ut,y_ut,z_ut,magnitude_ut,temperature_c"
print(header)
flash.write_line(header)

while True:
    elapsed_s = ticks_diff(ticks_ms(), start_ms) // 1000
    x_ut, y_ut, z_ut = sensor.magnetic_field_ut()
    magnitude_ut = sensor.magnitude_ut()
    temperature_c = sensor.temperature()

    line = "{},{:.2f},{:.2f},{:.2f},{:.2f},{:.2f}".format(
        elapsed_s,
        x_ut,
        y_ut,
        z_ut,
        magnitude_ut,
        temperature_c,
    )

    print(line)
    flash.write_line(line)

    if elapsed_s >= LOG_DURATION_S:
        break

    sleep_ms(SAMPLE_PERIOD_MS)

print()
print("Logging complete.")
print("The CSV file is available from the DAPLink USB mass storage.")
