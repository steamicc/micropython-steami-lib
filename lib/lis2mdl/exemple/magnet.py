from time import sleep_ms
from machine import I2C
from lis2mdl.device import LIS2MDL
import math

i2c = I2C(1)
mag = LIS2MDL(i2c)

print("Quick calibration: rotate the board FLAT over 360°...")
xmin = ymin =  1e9
xmax = ymax = -1e9

# capture ~3 seconds of data for min/max
for _ in range(150):
    x, y, z = mag.read_magnet()
    xmin = min(xmin, x); xmax = max(xmax, x)
    ymin = min(ymin, y); ymax = max(ymax, y)
    sleep_ms(20)

# offsets (hard-iron) and scales (simple 2D soft-iron)
x_off = (xmax + xmin) / 2.0
y_off = (ymax + ymin) / 2.0
x_scale = (xmax - xmin) / 2.0
y_scale = (ymax - ymin) / 2.0
# normalize the scale to have a circle (not essential but better)
scale = (x_scale + y_scale) / 2.0

print("Offsets:", x_off, y_off, "  Scales:", x_scale, y_scale)

print("\nContinuous reading (compass):")
while True:
    x, y, z = mag.read_magnet()

    # recentering + normalization
    x_c = (x - x_off) / scale
    y_c = (y - y_off) / scale

    # heading (adjust the sign according to your reference if needed)
    angle = math.degrees(math.atan2(y_c, x_c))
    if angle < 0:
        angle += 360
    
    direction = ""
    if angle >= 337.5 or angle < 22.5:
        direction = "N"
    elif angle >= 22.5 and angle < 67.5:
        direction = "NE"
    elif angle >= 67.5 and angle < 112.5:
        direction = "E"
    elif angle >= 112.5 and angle < 157.5:      
        direction = "SE"
    elif angle >= 157.5 and angle < 202.5:
        direction = "S"
    elif angle >= 202.5 and angle < 247.5:
        direction = "SW"
    elif angle >= 247.5 and angle < 292.5:
        direction = "W"
    elif angle >= 292.5 and angle < 337.5:
        direction = "NW"

    print("{} | {:.2f},{:.2f},{:.2f}  |  angle={:.2f}°".format(direction, x, y, z, angle))
    sleep_ms(100)
