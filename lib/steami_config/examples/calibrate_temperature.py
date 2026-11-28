"""Calibrate the temperature sensors of the board against its reference sensor.

The reference is the BME280 on a V1c and the WSEN-HIDS on a V1a/V1b. Every
other temperature sensor gets an offset so that it reads like the reference.
The offsets are stored in the persistent config zone, under the keys that
both the MicroPython and the Arduino libraries read ("bme", or "hid" and
"pad", plus "mag" and "ism"), and survive power cycles. The legacy "hts" key
of older versions of this tool is removed, never written.

Leave the board a few minutes at a stable room temperature, away from any
heat source, before running it.

Note: this example assumes the drivers are frozen into the firmware.
Use ``make micropython-firmware && make micropython-deploy`` to build a
firmware with the latest drivers before running this script.
"""

from time import sleep_ms

from steami import Release, Steami

release = Steami.begin()
if release == Release.UNKNOWN:
    raise SystemExit('Unknown board release: call Steami.begin("V1c") (or "V1b", "V1a").')

config = Steami.config()
if config is None:
    raise SystemExit("No config zone: update the DAPLink firmware of the board.")

# (config name, driver); the reference comes first.
if release == Release.V1C:
    sensors = [("bme280", Steami.bme280())]
else:
    sensors = [("wsen_hids", Steami.wsen_hids()), ("wsen_pads", Steami.wsen_pads())]
sensors += [("lis2mdl", Steami.lis2mdl()), ("ism330dl", Steami.ism330dl())]

ref_name, ref = sensors[0]
if ref is None:
    raise SystemExit("The reference sensor {} does not answer.".format(ref_name))

# Measure without any calibration, then let ISM330DL and LIS2MDL take a sample.
for _, sensor in sensors:
    if sensor is not None:
        sensor.set_temp_offset(0.0)
sleep_ms(200)

ref_temp = ref.temperature()
print("Board {}, reference {}: {:.2f} C".format(release, ref_name, ref_temp))
config.set_temperature_calibration(ref_name, gain=1.0, offset=0.0)
# steami reads the legacy "hts" entry when "hid" is the identity: drop it.
config.clear_temperature_calibration("hts221")

for name, sensor in sensors[1:]:
    if sensor is None:
        print("  {:10s}: does not answer, skipped".format(name))
        continue
    raw = sensor.temperature()
    offset = ref_temp - raw
    config.set_temperature_calibration(name, gain=1.0, offset=offset)
    print("  {:10s}: {:6.2f} C -> offset {:+.2f}".format(name, raw, offset))

config.save()
print("\nCalibration saved.")

# Verify: read the config zone back and apply it.
config.load()
print("\nVerification (after reload):")
for name, sensor in sensors:
    if sensor is not None:
        config.apply_temperature_calibration(sensor)
        print("  {:10s}: {:6.2f} C".format(name, sensor.temperature()))
