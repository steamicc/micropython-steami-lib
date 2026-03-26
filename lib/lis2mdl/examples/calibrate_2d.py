"""
Interactive hard-iron calibration.
Ask the user to slowly rotate the board flat on a table.
Uses calibrate_minmax_2d() to compute offsets, then displays before/after heading quality with calibrate_quality().
Demonstrates the full calibration workflow.
"""
from time import sleep_ms

from lis2mdl import LIS2MDL
from machine import I2C


def print_quality(title, quality):
    print(title)
    print("  mean_xy       = ({:.3f}, {:.3f})".format(quality["mean_xy"][0], quality["mean_xy"][1]))
    print("  mean_z        = {:.3f}".format(quality["mean_z"]))
    print("  std_xy        = ({:.3f}, {:.3f})".format(quality["std_xy"][0], quality["std_xy"][1]))
    print("  std_z         = {:.3f}".format(quality["std_z"]))
    print("  r_mean_xy     = {:.3f}".format(quality["r_mean_xy"]))
    print("  r_std_xy      = {:.3f}".format(quality["r_std_xy"]))
    print("  anisotropy_xy = {:.3f}".format(quality["anisotropy_xy"]))
    print()


i2c = I2C(1)
mag = LIS2MDL(i2c)

print("2D hard-iron calibration example")
print("Keep the board flat on a table.")
print("Slowly rotate it through full circles.")
print()

print("Checking heading quality before calibration...")
quality_before = mag.calibrate_quality(samples_check=120, delay_ms=15)
print_quality("Before calibration:", quality_before)

print("Starting 2D calibration now...")
mag.calibrate_minmax_2d(samples=300, delay_ms=20)

print("Calibration values:")
print(
    "  x_off={:.2f}  y_off={:.2f}  x_scale={:.2f}  y_scale={:.2f}".format(
        mag.x_off, mag.y_off, mag.x_scale, mag.y_scale
    )
)
print()

print("Checking heading quality after calibration...")
quality_after = mag.calibrate_quality(samples_check=120, delay_ms=15)
print_quality("After calibration:", quality_after)

print("Live heading preview after calibration")
print("Press Ctrl+C to stop.")
print()

while True:
    heading = mag.heading_flat_only()
    direction = mag.direction_label(heading)
    print("Heading: {:7.2f} deg  Direction: {}".format(heading, direction))
    sleep_ms(200)
