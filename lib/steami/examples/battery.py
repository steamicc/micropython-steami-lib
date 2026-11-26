"""Print the battery charge, voltage and current once per second.

Works on every release (V1a, V1b and V1c): the BQ27441 gauge. The current is
positive while the battery charges. Without a battery, the gauge does not
answer.

If the gauge does not answer, begin() returns False and error() says why; the
library also prints one message with its code.
"""

from time import sleep

from steami import Battery

battery = Battery()

if battery.begin():
    print("Battery gauge:", battery.chip())
else:
    print("No battery gauge:", battery.error())

while True:
    if battery.is_available():
        print(
            "{} %, {:.2f} V, {} mA{}".format(
                battery.percent(),
                battery.voltage(),
                battery.current(),
                " (charging)" if battery.is_charging() else "",
            )
        )
    sleep(1)
