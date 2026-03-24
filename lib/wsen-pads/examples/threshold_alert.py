"""Monitor pressure continuously and print an alert when pressure drops below a configurable threshold (e.g. storm detection)."""

from time import sleep

from machine import I2C
from wsen_pads import WSEN_PADS
from wsen_pads.const import ODR_10_HZ

PRESSURE_ALERT_HPA = 1000 # Alert threshold
READ_INTERVAL_S = 1 # Time between printed readings

i2c = I2C(1)
sensor = WSEN_PADS(i2c)

sensor.set_continuous(odr=ODR_10_HZ)

print("Pressure monitor started")
print("Alert threshold:", PRESSURE_ALERT_HPA, "hPa")

alert_active = False

while True:
    pressure = sensor.pressure_hpa()

    # Threshold detection
    if pressure < PRESSURE_ALERT_HPA:
        if not alert_active:
            print("ALERT: pressure dropped below", PRESSURE_ALERT_HPA, "hPa")
            alert_active = True
    else:
        if alert_active:
            print("INFO: pressure back above", PRESSURE_ALERT_HPA, "hPa")
        alert_active = False

    sleep(READ_INTERVAL_S)
