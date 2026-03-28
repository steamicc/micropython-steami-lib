"""
Heading that works even when the board is tilted.
Combine heading_with_tilt_compensation() with the ISM330DL accelerometer.
Show heading + pitch/roll. Demonstrates cross-sensor fusion (magnetometer + accelerometer).
"""

from math import atan2, degrees, sqrt
from time import sleep_ms

from ism330dl import ISM330DL
from lis2mdl import LIS2MDL
from machine import I2C


def pitch_roll_from_accel(ax, ay, az):
    roll_rad = atan2(ay, az)
    pitch_rad = atan2(-ax, sqrt(ay * ay + az * az))
    return degrees(pitch_rad), degrees(roll_rad)


i2c = I2C(1)
mag = LIS2MDL(i2c)
imu = ISM330DL(i2c)

print("Tilt-compensated heading example")
print("This example uses LIS2MDL + ISM330DL.")
print("Rotate the board in all directions for 3D magnetometer calibration.")
print()

mag.calibrate_minmax_3d(samples=400, delay_ms=20)
mag.set_heading_filter(0.2)

print("Calibration done.")
print("Press Ctrl+C to stop.")
print()

while True:
    accel = imu.acceleration_g()
    ax, ay, az = accel

    heading = mag.heading_with_tilt_compensation(lambda a=accel: a)
    pitch_deg, roll_deg = pitch_roll_from_accel(ax, ay, az)
    direction = mag.direction_label(heading)

    print(
        "Heading={:7.2f} deg  Dir={}  Pitch={:7.2f} deg  Roll={:7.2f} deg".format(
            heading, direction, pitch_deg, roll_deg
        )
    )

    sleep_ms(200)
