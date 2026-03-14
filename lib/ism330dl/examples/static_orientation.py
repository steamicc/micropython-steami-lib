from machine import I2C
from time import sleep_ms
from ism330dl import ISM330DL

i2c = I2C(1)

imu = ISM330DL(i2c)

print("ISM330DL orientation demo")
print()


# -------------------------------------------------
# Main loop
# -------------------------------------------------

while True:
    dir = imu.orientation()

    print("Orientation: {}".format(dir))

    sleep_ms(500)
