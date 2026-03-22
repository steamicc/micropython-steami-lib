from machine import I2C
from time import sleep_ms
from ism330dl import ISM330DL

i2c = I2C(1)

imu = ISM330DL(i2c)

print("ISM330DL example: basic read")
print()

while True:

    ax, ay, az = imu.acceleration_g()
    gx, gy, gz = imu.gyroscope_dps()
    temp = imu.temperature()

    print(
        "A[g]=({:+.2f},{:+.2f},{:+.2f})  "
        "G[dps]=({:+.1f},{:+.1f},{:+.1f})  "
        "T={:.1f}°C".format(
            ax, ay, az,
            gx, gy, gz,
            temp
        )
    )

    sleep_ms(500)
