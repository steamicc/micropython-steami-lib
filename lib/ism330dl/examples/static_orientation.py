from time import sleep_ms

from ism330dl import ISM330DL
from machine import I2C

i2c = I2C(1)

imu = ISM330DL(i2c)

print("ISM330DL orientation demo")
print()


# -------------------------------------------------
# Main loop
# -------------------------------------------------

while True:
    direction = imu.orientation()

    print("Orientation: {}".format(direction))

    sleep_ms(500)
