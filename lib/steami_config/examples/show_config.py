"""Display the current board configuration stored in the config zone."""

from daplink_bridge import DaplinkBridge
from machine import I2C
from steami_config import SteamiConfig


def print_section(title):
    print(title)
    print("-" * len(title))


def print_kv(label, value):
    print("{:<16} {}".format(label + ":", value))


i2c = I2C(1)
bridge = DaplinkBridge(i2c)
config = SteamiConfig(bridge)
config.load()

print("=== STeaMi Configuration ===")
print()

# --------------------------------------------------
# Board info
# --------------------------------------------------

print_section("Board info")
rev = config.board_revision
name = config.board_name

print_kv("Board revision", rev if rev is not None else "(not set)")
print_kv("Board name", name if name is not None else "(not set)")
print()

# --------------------------------------------------
# Temperature calibration
# --------------------------------------------------

print_section("Temperature calibration")
sensors = ["hts221", "lis2mdl", "ism330dl", "wsen_hids", "wsen_pads"]

has_temp_cal = False
for sensor in sensors:
    cal = config.get_temperature_calibration(sensor)
    if cal is not None:
        has_temp_cal = True
        print(
            "  {:10s}  gain={:.4f}  offset={:+.2f} C".format(
                sensor,
                cal["gain"],
                cal["offset"],
            )
        )

if not has_temp_cal:
    print("  (none)")
print()

# --------------------------------------------------
# Magnetometer calibration
# --------------------------------------------------

print_section("Magnetometer calibration")
mag_cal = config.get_magnetometer_calibration()

if mag_cal is None:
    print("  (none)")
else:
    print("  Hard iron offsets:")
    print(
        "    x={:+.4f}  y={:+.4f}  z={:+.4f}".format(
            mag_cal["hard_iron_x"],
            mag_cal["hard_iron_y"],
            mag_cal["hard_iron_z"],
        )
    )
    print("  Soft iron scales:")
    print(
        "    x={:.4f}  y={:.4f}  z={:.4f}".format(
            mag_cal["soft_iron_x"],
            mag_cal["soft_iron_y"],
            mag_cal["soft_iron_z"],
        )
    )
print()

# --------------------------------------------------
# Accelerometer calibration
# --------------------------------------------------

print_section("Accelerometer calibration")
accel_cal = config.get_accelerometer_calibration()

if accel_cal is None:
    print("  (none)")
else:
    print(
        "  Offsets (g): x={:+.4f}  y={:+.4f}  z={:+.4f}".format(
            accel_cal["ox"],
            accel_cal["oy"],
            accel_cal["oz"],
        )
    )
print()

# --------------------------------------------------
# Boot counter
# --------------------------------------------------

print_section("Boot counter")
boot_count = config.get_boot_count()
print("  {}".format(boot_count if boot_count is not None else "(not set)"))
print()

# --------------------------------------------------
# Raw JSON
# --------------------------------------------------

print_section("Raw JSON")
print(config._data)
