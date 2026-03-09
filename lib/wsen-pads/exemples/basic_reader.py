from machine import I2C, Pin
from time import sleep
from wsen_pads import WSEN_PADS


# Update the I2C bus number and pins to match your board
i2c = I2C(1)

# Create the sensor object
pads = WSEN_PADS(i2c)

print("WSEN-PADS found")
print("Device ID:", hex(pads.device_id()))

for _ in range(10):
    pressure_hpa, temperature_c = pads.read()

    pressure_hpa = pads.pressure()
    temperature_c = pads.temperature()

    print("P:", pressure_hpa, "hPa  T:", temperature_c, "°C")

    sleep(0.5)