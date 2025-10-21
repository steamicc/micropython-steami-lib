from time import sleep_ms
from machine import I2C
from lis2mdl.device import LIS2MDL

# Initialize the LIS2MDL magnetometer
i2c = I2C(1)
magnetometer = LIS2MDL(i2c)

print("Starting magnetometer readings...")

while True:
    # Read magnetic field data
    magnet = magnetometer.read_magnet()
    print(f"Magnetic field (X, Y, Z): {magnet}")

    # Wait for 1 second
    sleep_ms(1000)