"""Log sensor data to flash and compute statistics.

Writes 200 rows of simulated sensor data (temperature, humidity, pressure)
to a CSV file on flash, then reads it back and computes min/max/average
for each column.
"""

from time import sleep_ms

from daplink_bridge import DaplinkBridge
from daplink_flash import DaplinkFlash
from machine import I2C

# --- Configuration ---
NUM_ROWS = 200
FILENAME = "SENSORS"
EXT = "CSV"

# --- Init ---
i2c = I2C(1)
bridge = DaplinkBridge(i2c)
flash = DaplinkFlash(bridge)
print("DAPLink Flash WHO_AM_I: 0x{:02X}".format(bridge.device_id()))

# --- Generate and write data ---
print("Writing {} rows to {}.{} ...".format(NUM_ROWS, FILENAME, EXT))
flash.set_filename(FILENAME, EXT)
flash.clear_flash()
sleep_ms(500)

flash.write_line("row;temperature;humidity;pressure")

# Simple pseudo-random generator (linear congruential)
seed = 12345
for row in range(NUM_ROWS):
    seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
    temp = 20.0 + (seed % 1000) / 100.0
    seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
    hum = 30.0 + (seed % 4000) / 100.0
    seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
    pres = 990.0 + (seed % 5000) / 100.0

    line = "{};{:.1f};{:.1f};{:.1f}".format(row, temp, hum, pres)
    flash.write(line + "\n")

print("Write complete.")
sleep_ms(100)

# --- Read back and compute statistics ---
print("Reading back...")
content = flash.read()
lines = content.decode().split("\n")

# Skip header and empty lines
data_lines = [l for l in lines[1:] if l]
print("Read {} data rows.".format(len(data_lines)))

temp_sum = 0.0
hum_sum = 0.0
pres_sum = 0.0
temp_min = 999.0
temp_max = -999.0
hum_min = 999.0
hum_max = -999.0
pres_min = 9999.0
pres_max = -9999.0
count = 0

for line in data_lines:
    parts = line.split(";")
    if len(parts) != 4:
        continue
    t = float(parts[1])
    h = float(parts[2])
    p = float(parts[3])

    temp_sum += t
    hum_sum += h
    pres_sum += p

    temp_min = min(temp_min, t)
    temp_max = max(temp_max, t)
    hum_min = min(hum_min, h)
    hum_max = max(hum_max, h)
    pres_min = min(pres_min, p)
    pres_max = max(pres_max, p)

    count += 1

print()
print("=== Statistics ({} rows) ===".format(count))
print("              Min      Avg      Max")
print("Temp (C):  {:7.1f}  {:7.1f}  {:7.1f}".format(
    temp_min, temp_sum / count, temp_max))
print("Hum (%):   {:7.1f}  {:7.1f}  {:7.1f}".format(
    hum_min, hum_sum / count, hum_max))
print("Pres (hPa):{:7.1f}  {:7.1f}  {:7.1f}".format(
    pres_min, pres_sum / count, pres_max))
print()
print("File size: {} bytes".format(len(content)))
