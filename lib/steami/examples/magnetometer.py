"""Print the magnetic field measured by the LIS2MDL twice per second.

Works on every release (V1a, V1b and V1c). Values are in microtesla. The
hard-iron offset is removed only after a calibration (the "cm" key of the board
config, or calibrate()); before that the values include the board's own field
and can be much larger than the Earth field (about 25 to 65 uT).

Press MENU to calibrate for 12 seconds: turn the board slowly in every direction
meanwhile. The calibration lives in RAM and is lost on reset.

If the sensor does not answer, begin() returns False and error() says why; the
library also prints one message with its code.
"""

from time import sleep_ms, ticks_diff, ticks_ms

from steami import Buttons, Magnetometer

magnetometer = Magnetometer()
buttons = Buttons()

if magnetometer.begin():
    print("Magnetometer:", magnetometer.chip(), "- press MENU to calibrate (12 s).")
else:
    print("No magnetometer:", magnetometer.error())
buttons.begin()

last_print = ticks_ms()
while True:
    # Poll the buttons often: a short tap is missed if they are read only twice per second.
    if buttons.was_pressed("MENU"):
        print("Calibrating: turn the board in every direction...")
        magnetometer.calibrate(12)
        print("Calibration done.")
        last_print = ticks_ms()

    if ticks_diff(ticks_ms(), last_print) >= 500:
        last_print = ticks_ms()
        x, y, z = magnetometer.read()
        print(
            "x={:.1f} y={:.1f} z={:.1f} uT, strength {:.1f}".format(
                x, y, z, magnetometer.strength()
            )
        )
    sleep_ms(5)
