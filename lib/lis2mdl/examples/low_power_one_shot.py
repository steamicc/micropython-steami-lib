"""
Energy-efficient sampling.
Use power_off() between readings, trigger read_one_shot() every 10s.
Print values and free memory.
Demonstrates idle mode for battery-powered deployments.
"""

import gc
from math import sqrt
from time import sleep_ms

from lis2mdl import LIS2MDL
from machine import I2C

MAG_LSB_TO_UT = 0.15
SAMPLE_INTERVAL_MS = 10000


i2c = I2C(1)
mag = LIS2MDL(i2c)

print("Low-power one-shot example")
print("The sensor stays in idle mode between readings.")
print("One sample every 10 seconds.")
print()

while True:
    mag.power_off()

    # Sleep in small steps so Ctrl+C remains responsive.
    for _ in range(SAMPLE_INTERVAL_MS // 100):
        sleep_ms(100)

    raw_x, raw_y, raw_z = mag.read_one_shot()
    temp_c = mag.temperature()

    x_ut = raw_x * MAG_LSB_TO_UT
    y_ut = raw_y * MAG_LSB_TO_UT
    z_ut = raw_z * MAG_LSB_TO_UT
    magnitude_ut = sqrt(x_ut * x_ut + y_ut * y_ut + z_ut * z_ut)

    gc.collect()
    free_mem = gc.mem_free()

    print(
        "One-shot read: X={:.2f} uT  Y={:.2f} uT  Z={:.2f} uT  |B|={:.2f} uT  Temp={:.2f} C  Free mem={} bytes".format(
            x_ut, y_ut, z_ut, magnitude_ut, temp_c, free_mem
        )
    )
