"""Loop that reads pressure + temperature every 5s, computes altitude, prints a formatted summary, and logs each measurement to a CSV file on the DAPLink flash using daplink_flash (set_filename, write_line). The file can then be read back from USB mass storage."""

from time import sleep, sleep_ms

from daplink_flash import DaplinkFlash
from machine import I2C
from wsen_pads import WSEN_PADS
from wsen_pads.const import ODR_10_HZ

i2c = I2C(1)

sensor = WSEN_PADS(i2c)
flash = DaplinkFlash(i2c)

sensor.set_continuous(odr=ODR_10_HZ)

# Set filename and erase
flash.set_filename("weather_station", "CSV")
flash.clear_flash()
sleep_ms(500)
print("Flash erased.")

flash.write_line("temperature;pressure")

while True:
    pressure = sensor.pressure_hpa()
    temperature = sensor.temperature()

    print("P:", pressure, "hPa  T:", temperature, "°C")
    flash.write_line(f"{temperature};{pressure}")

    sleep(0.1)
