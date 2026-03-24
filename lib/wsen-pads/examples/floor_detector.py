"""Measure altitude at startup as baseline, then loop and detect floor changes (each ~3m altitude difference = 1 floor). Print "Floor +1", "Floor -1", etc."""

from time import sleep

from machine import I2C
from wsen_pads import WSEN_PADS
from wsen_pads.const import ODR_10_HZ

i2c = I2C(1)
sensor = WSEN_PADS(i2c)
sensor.set_continuous(odr=ODR_10_HZ)

SAMPLES_FOR_BASELINE = 20
SAMPLES_PER_MEASURE = 10
SEA_LEVEL_HPA = 1013.25
METERS_PER_FLOOR = 0.1 #3.0

baseline_pressure_list = []

print("Measuring baseline pressure...")
for _ in range(SAMPLES_FOR_BASELINE):
    pressure = sensor.pressure_hpa()
    baseline_pressure_list.append(pressure)

    sleep(0.5)

baseline_pressure = sum(baseline_pressure_list) / len(baseline_pressure_list)
print("Baseline pressure:", baseline_pressure, "hPa")

while True:
    pressure_samples = []

    print("Measuring...")
    for _ in range(SAMPLES_PER_MEASURE):
        pressure = sensor.pressure_hpa()
        pressure_samples.append(pressure)

        sleep(0.5)

    avg_pressure = sum(pressure_samples) / len(pressure_samples)

    # Calculate altitude difference from baseline using barometric formula
    altitude_diff = 44330 * (1 - (avg_pressure / baseline_pressure) ** (1/5.255))

    floor_change = round(altitude_diff / METERS_PER_FLOOR)

    print("Avg Pressure:", avg_pressure, "hPa  Altitude Diff:", altitude_diff, "m  Floor Change:", floor_change)
