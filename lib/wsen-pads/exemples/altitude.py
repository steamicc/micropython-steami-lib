from machine import I2C, Pin
from time import sleep
from wsen_pads import WSEN_PADS

SEA_LEVEL_PRESSURE = 1013.25 # depends on your location, you can adjust it for better altitude estimation
EXPONENT = 0.1903 # standard atmosphere exponent for altitude calculation

i2c = I2C(1)

sensor = WSEN_PADS(i2c)

def pressure_to_altitude(p):
    return 44330 * (1 - (p / SEA_LEVEL_PRESSURE) ** EXPONENT)

for _ in range(10):
    pressure, temp = sensor.read()

    altitude = pressure_to_altitude(pressure)

    print("Pressure:", pressure, "hPa")
    print("Altitude:", altitude, "m")
    print()

    sleep(0.5)
