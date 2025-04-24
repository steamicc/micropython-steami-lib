from time import sleep

from machine import I2C

from bq27441 import BQ27441

bus = I2C(1)

fg = BQ27441(bus)

print("Fuel Gauge Test")
print("=====================")

while True:
    print("State of Charge:", fg.state_of_charge(), "%")
    print("Battery Voltage:", fg.voltage(), "mV")
    print("Average Current:", fg.current_average(), "mA")
    print("Full Capacity:", fg.capacity_full(), "/")
    print("Remaining Capacity:", fg.capacity_remaining(), "mAh")
    sleep(10)
