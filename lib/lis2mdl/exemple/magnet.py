from time import sleep_ms
from machine import I2C
from lis2mdl.device import LIS2MDL

i2c = I2C(1)
mag = LIS2MDL(i2c)

mag.calibrate_step()
calibration_values = mag.get_calibration()
print("x_off, y_off, z_off, x_scale, y_scale, z_scale :")
print(calibration_values)

print("Lecture continue (boussole):")
while True:
    angle = mag.heading_flat_only()
    dir8 = mag.direction_label(angle)
    
    print(f"{dir8} | angle={angle:.2f}°")
    sleep_ms(100)