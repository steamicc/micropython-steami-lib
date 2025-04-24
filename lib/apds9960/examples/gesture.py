from time import sleep

from machine import I2C

from apds9960.const import (
    APDS9960_DIR_NONE,
    APDS9960_DIR_LEFT,
    APDS9960_DIR_RIGHT,
    APDS9960_DIR_UP,
    APDS9960_DIR_DOWN,
    APDS9960_DIR_NEAR,
    APDS9960_DIR_FAR,
)
from apds9960 import uAPDS9960 as APDS9960

bus = I2C(1)

apds = APDS9960(bus)

dirs = {
    APDS9960_DIR_NONE: "none",
    APDS9960_DIR_LEFT: "left",
    APDS9960_DIR_RIGHT: "right",
    APDS9960_DIR_UP: "up",
    APDS9960_DIR_DOWN: "down",
    APDS9960_DIR_NEAR: "near",
    APDS9960_DIR_FAR: "far",
}

apds.setProximityIntLowThreshold(50)

print("Gesture Test")
print("============")
apds.enableGestureSensor()

while True:
    sleep(0.5)
    if apds.isGestureAvailable():
        motion = apds.readGesture()
        print("Gesture={}".format(dirs.get(motion, "unknown")))
