"""
Detect door open/close using a magnet.
Measure baseline field with door closed (magnet near sensor).
Loop and detect large magnitude drop = door opened. Print state changes with timestamp.
Demonstrates a practical IoT use case.
"""

from time import sleep_ms, ticks_diff, ticks_ms

from lis2mdl import LIS2MDL
from machine import I2C

BASELINE_SAMPLES = 60
OPEN_DROP_UT = 10.0
CLOSE_RECOVER_UT = 6.0


def elapsed_seconds(start_ms):
    return ticks_diff(ticks_ms(), start_ms) / 1000.0


i2c = I2C(1)
mag = LIS2MDL(i2c)

print("Door sensor example")
print("Place the board with the door closed and the magnet in its normal closed position.")
print("Measuring closed-door baseline...")
print()

baseline = 0.0
for _ in range(BASELINE_SAMPLES):
    baseline += mag.magnitude_ut()
    sleep_ms(100)

baseline /= BASELINE_SAMPLES
start_ms = ticks_ms()
state = "CLOSED"

print("Closed baseline: {:.2f} uT".format(baseline))
print("Monitoring door state changes...")
print()

while True:
    magnitude = mag.magnitude_ut()
    drop = baseline - magnitude

    if state == "CLOSED" and drop >= OPEN_DROP_UT:
        state = "OPEN"
        print("[t+{:.1f}s] Door opened  |B|={:.2f} uT  drop={:.2f} uT".format(
            elapsed_seconds(start_ms), magnitude, drop
        ))

    elif state == "OPEN" and drop <= CLOSE_RECOVER_UT:
        state = "CLOSED"
        print("[t+{:.1f}s] Door closed  |B|={:.2f} uT  drop={:.2f} uT".format(
            elapsed_seconds(start_ms), magnitude, drop
        ))

    sleep_ms(200)
