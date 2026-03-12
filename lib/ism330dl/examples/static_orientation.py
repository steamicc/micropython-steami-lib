from machine import I2C, Pin
from time import sleep
from ism330dl import ISM330DL

i2c = I2C(1)

imu = ISM330DL(i2c, address=0x6B)

print("ISM330DL orientation demo")
print()


# -------------------------------------------------
# Main loop
# -------------------------------------------------

while True:
    dir = imu.orientation()

    print("Orientation: {}".format(dir))

    sleep(0.5)
