from machine import I2C
from time import sleep
from ism330dl import ISM330DL

i2c = I2C(1)

imu = ISM330DL(i2c, address=0x6B)

print("ISM330DL gyroscope direction demo")
print()

while True:
    motion, speed = imu.motion()

    print("Motion: {}  Speed: {:.1f} dps".format(motion, speed))

    sleep(0.2)
