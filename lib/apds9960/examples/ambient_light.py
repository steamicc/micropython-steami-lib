from time import sleep

from machine import I2C

from apds9960 import uAPDS9960 as APDS9960

i2c = I2C(1)

apds = APDS9960(i2c)

print("Light Sensor Test")
print("=================")
apds.enable_light_sensor()

oval = -1
while True:
    sleep(0.25)
    val = apds.read_ambient_light()
    if val != oval:
        print("AmbientLight={}".format(val))
        oval = val
