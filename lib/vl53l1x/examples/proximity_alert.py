"""Proximity alert using VL53L1X distance sensor and buzzer.

Beeps the buzzer when an object is detected within 200 mm. The pitch
increases as the object gets closer.
"""

from time import sleep_ms

from machine import I2C, Pin
from pyb import Timer
from vl53l1x import VL53L1X

DISTANCE_THRESHOLD_MM = 200

# Sensor configuration
i2c = I2C(1)
tof = VL53L1X(i2c)

# Buzzer initialisation
buzzer_tim = Timer(1, freq=1000)
buzzer_ch = buzzer_tim.channel(4, Timer.PWM, pin=Pin("SPEAKER"))
buzzer_ch.pulse_width_percent(0)

try:
    while True:
        distance = tof.read()
        print("Distance: {} mm".format(distance))

        if distance < DISTANCE_THRESHOLD_MM:
            # Frequency ranging from 1500 (really close) to 500 (at 200mm)
            freq = 1500 - (distance * 5)
            # Security limits
            freq = max(500, min(1500, freq))

            buzzer_tim.freq(freq)
            buzzer_ch.pulse_width_percent(50)
        else:
            buzzer_ch.pulse_width_percent(0)

        sleep_ms(50)

except KeyboardInterrupt:
    pass
finally:
    buzzer_ch.pulse_width_percent(0)
