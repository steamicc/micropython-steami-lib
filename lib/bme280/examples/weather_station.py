"""Continuous weather monitoring with altitude estimation.

Reads temperature, pressure, and humidity every 5 seconds in normal mode,
computes approximate altitude from pressure using the barometric formula,
and logs each measurement to the DAPLink flash as CSV.
"""

from time import sleep, sleep_ms

from bme280 import BME280
from bme280.const import FILTER_16, OSRS_X2, OSRS_X16, STANDBY_1000_MS
from daplink_bridge import DaplinkBridge
from daplink_flash import DaplinkFlash
from machine import I2C

# Sea-level reference pressure in hPa (adjust to local conditions)
SEA_LEVEL_PRESSURE = 1013.25

i2c = I2C(1)

sensor = BME280(i2c)
bridge = DaplinkBridge(i2c)
flash = DaplinkFlash(bridge)

# Configure for weather monitoring: high pressure resolution, moderate temp/hum
sensor.set_oversampling(temperature=OSRS_X2, pressure=OSRS_X16, humidity=OSRS_X2)
sensor.set_iir_filter(FILTER_16)
sensor.set_continuous(standby=STANDBY_1000_MS)

# Prepare flash logging
flash.set_filename("WEATHER", "CSV")
flash.clear_flash()
sleep_ms(500)
print("Flash erased.")

flash.write_line("temperature;pressure;humidity;altitude")


def altitude_m(pressure_hpa):
    """Estimate altitude in meters from pressure using the barometric formula."""
    return 44330.0 * (1.0 - (pressure_hpa / SEA_LEVEL_PRESSURE) ** 0.1903)


while True:
    temperature, pressure, humidity = sensor.read()
    alt = altitude_m(pressure)

    print(
        "T: {:.1f} C  P: {:.1f} hPa  H: {:.1f} %RH  Alt: {:.0f} m".format(
            temperature, pressure, humidity, alt
        )
    )
    flash.write_line(
        "{:.1f};{:.1f};{:.1f};{:.0f}".format(temperature, pressure, humidity, alt)
    )

    sleep(5)
