from machine import I2C
from time import sleep

from wsen_pads import WSEN_PADS

# Set your known altitude (in meters) for calibration
KNOWN_ALTITUDE = 12  # Example: your location altitude

i2c = I2C(1)
sensor = WSEN_PADS(i2c)


pressure = sensor.pressure_hpa()

# Compute sea-level pressure based on known altitude
# Formula derived from barometric equation
sea_level_pressure = pressure / (1 - (KNOWN_ALTITUDE / 44330.0)) ** 5.255

print("Calibration:")
print("  Measured pressure: {:.1f} hPa".format(pressure))
print("  Known altitude:    {:.1f} m".format(KNOWN_ALTITUDE))
print("  Sea-level pressure: {:.1f} hPa".format(sea_level_pressure))
print("-" * 50)

while True:
    pressure = sensor.pressure_hpa()

    # Compute altitude using calibrated sea-level pressure
    altitude = 44330.0 * (1 - (pressure / sea_level_pressure) ** (1 / 5.255))

    print("Altitude: {:6.1f} m | Pressure: {:6.1f} hPa".format(altitude, pressure))

    sleep(1)
