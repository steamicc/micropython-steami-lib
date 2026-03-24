from time import sleep_ms

from ism330dl import ISM330DL
from machine import I2C

i2c = I2C(1)

imu = ISM330DL(i2c)

print("ISM330DL gyroscope direction demo")
print()

while True:
    motion, speed = imu.motion()

    print("Motion: {}  Speed: {:.1f} dps".format(motion, speed))

    sleep_ms(200)
