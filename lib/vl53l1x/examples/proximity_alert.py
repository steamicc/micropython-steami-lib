"""Proximity alert using VL53L1X distance sensor and buzzer.

Beeps the buzzer when an object is detected within 200 mm. The pitch
increases as the object gets closer.
"""

from time import sleep_ms

from machine import I2C
from steami import no_tone, tone
from vl53l1x import VL53L1X

DISTANCE_THRESHOLD_MM = 200

# Sensor configuration
i2c = I2C(1)
tof = VL53L1X(i2c)

try:
    while True:
        distance = tof.read()
        print("Distance: {} mm".format(distance))

        if distance < DISTANCE_THRESHOLD_MM:
            # Frequency ranging from 1500 (really close) to 500 (at 200mm)
            freq = 1500 - (distance * 5)
            # Security limits
            freq = max(500, min(1500, freq))

            tone(freq)
        else:
            no_tone()

        sleep_ms(50)

except KeyboardInterrupt:
    pass
finally:
    no_tone()
