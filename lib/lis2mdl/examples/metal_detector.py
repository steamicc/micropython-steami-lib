"""
Detect nearby metal objects by monitoring field magnitude changes.
Measure a baseline, then loop and print an alert (with intensity bar) when magnitude deviates significantly.
Louder buzzer beep for stronger fields — like a real metal detector.
"""

from time import sleep_ms, ticks_ms

from lis2mdl import LIS2MDL
from machine import I2C, Pin

SPEAKER = Pin("SPEAKER", Pin.OUT)

BASELINE_SAMPLES = 30
BASELINE_DELAY_MS = 100

MIN_ALERT_DELTA_UT = 8.0
MAX_ALERT_DELTA_UT = 60.0
BAR_WIDTH = 20


def tone(pin, freq, duration_ms):
    """Generate a square wave on the buzzer pin."""
    if freq == 0:
        sleep_ms(duration_ms)
        return

    period_us = int(1_000_000 / freq)
    half_period_us = period_us // 2
    end_time = ticks_ms() + duration_ms

    while ticks_ms() < end_time:
        pin.on()
        sleep_ms(max(1, half_period_us // 1000))
        pin.off()
        sleep_ms(max(1, half_period_us // 1000))


def make_bar(value, max_value, width=20):
    """Build a simple text bar for alert intensity."""
    clamped = min(max(value, 0.0), max_value)
    filled = int((clamped / max_value) * width)
    return "#" * filled + "-" * (width - filled)


def alert_tone(delta_ut):
    """Play a stronger tone when the magnetic disturbance is larger."""
    normalized = min(delta_ut, MAX_ALERT_DELTA_UT) / MAX_ALERT_DELTA_UT
    freq = int(1200 + normalized * 1800)
    duration_ms = int(40 + normalized * 80)
    tone(SPEAKER, freq, duration_ms)


i2c = I2C(1)
sensor = LIS2MDL(i2c)

print("LIS2MDL metal detector example")
print("Keep the board away from metal during baseline capture.")
print()

baseline_values = []
for _ in range(BASELINE_SAMPLES):
    baseline_values.append(sensor.magnitude_ut())
    sleep_ms(BASELINE_DELAY_MS)

baseline_ut = sum(baseline_values) / len(baseline_values)

print("Baseline magnitude: {:.2f} uT".format(baseline_ut))
print("Move a metal object near the sensor.")
print("Press Ctrl+C to stop.")
print()

while True:
    magnitude_ut = sensor.magnitude_ut()
    delta_ut = abs(magnitude_ut - baseline_ut)
    bar = make_bar(delta_ut, MAX_ALERT_DELTA_UT, BAR_WIDTH)

    if delta_ut >= MIN_ALERT_DELTA_UT:
        print(
            "ALERT  |B|={:.2f} uT  delta={:.2f} uT  [{}]".format(
                magnitude_ut,
                delta_ut,
                bar,
            )
        )
        alert_tone(delta_ut)
    else:
        print(
            "CLEAR  |B|={:.2f} uT  delta={:.2f} uT  [{}]".format(
                magnitude_ut,
                delta_ut,
                bar,
            )
        )
        sleep_ms(100)

    sleep_ms(100)
