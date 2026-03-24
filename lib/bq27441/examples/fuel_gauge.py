from time import sleep

from bq27441 import BQ27441
from machine import I2C

i2c = I2C(1)

fg = BQ27441(i2c)

print("Fuel Gauge Test")
print("=====================")

while True:
    print("State of Charge:", fg.state_of_charge(), "%")
    print("Battery Voltage:", fg.voltage_mv(), "mV")
    print("Average Current:", fg.current_average(), "mA")
    print("Full Capacity:", fg.capacity_full(), "/")
    print("Remaining Capacity:", fg.capacity_remaining(), "mAh")
    sleep(10)
