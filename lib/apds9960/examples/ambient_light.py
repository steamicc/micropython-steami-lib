from time import sleep

from machine import I2C

from apds9960 import uAPDS9960 as APDS9960

bus = I2C(1)

apds = APDS9960(bus)

print("Light Sensor Test")
print("=================")
apds.enableLightSensor()

oval = -1
while True:
    sleep(0.25)
    val = apds.readAmbientLight()
    if val != oval:
        print("AmbientLight={}".format(val))
        oval = val
