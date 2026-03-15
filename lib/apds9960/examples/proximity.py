from time import sleep

from machine import I2C

from apds9960 import uAPDS9960 as APDS9960

i2c = I2C(1)

apds = APDS9960(i2c)

apds.set_proximity_int_low_threshold(50)

print("Proximity Sensor Test")
print("=====================")
apds.enable_proximity_sensor()

oval = -1
while True:
    sleep(0.25)
    val = apds.read_proximity()
    if val != oval:
        print("proximity={}".format(val))
        oval = val
