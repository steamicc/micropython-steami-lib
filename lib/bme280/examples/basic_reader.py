from time import sleep

from bme280 import BME280
from machine import I2C

# Update the I2C bus number and pins to match your board
i2c = I2C(1)

# Create the sensor object
sensor = BME280(i2c)

print("BME280 found")
print("Device ID:", hex(sensor.device_id()))

for _ in range(10):
    temperature, pressure, humidity = sensor.read_one_shot()

    print(
        "T: {:.1f} C  P: {:.1f} hPa  H: {:.1f} %RH".format(
            temperature, pressure, humidity
        )
    )

    sleep(1)
