from machine import I2C, Pin
from time import sleep
from ism330dl import ISM330DL
from ism330dl.const import *


# ---------------------------------------------------------------------
# Update these pins and bus number to match your board
# ---------------------------------------------------------------------
TEMP_MIN = -40.0
TEMP_MAX = 85.0
ACCEL_MIN_G = 0.5
ACCEL_MAX_G = 1.5


def print_header(title):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def print_pass(name):
    print("[PASS] {}".format(name))


def print_fail(name, err=None):
    if err is None:
        print("[FAIL] {}".format(name))
    else:
        print("[FAIL] {} -> {}".format(name, err))


def dump_registers(sensor):
    who_am_i = sensor._read_u8(REG_WHO_AM_I)
    ctrl1_xl = sensor._read_u8(REG_CTRL1_XL)
    ctrl2_g = sensor._read_u8(REG_CTRL2_G)
    ctrl3_c = sensor._read_u8(REG_CTRL3_C)
    status = sensor._read_u8(REG_STATUS_REG)

    print("WHO_AM_I   = 0x{:02X}".format(who_am_i))
    print("CTRL1_XL   = 0x{:02X}".format(ctrl1_xl))
    print("CTRL2_G    = 0x{:02X}".format(ctrl2_g))
    print("CTRL3_C    = 0x{:02X}".format(ctrl3_c))
    print("STATUS_REG = 0x{:02X}".format(status))


def test_i2c_scan(i2c):
    print_header("1) I2C scan")
    devices = i2c.scan()
    print("I2C devices found:", [hex(x) for x in devices])

    if ISM330DL_I2C_ADDR_LOW in devices or ISM330DL_I2C_ADDR_HIGH in devices:
        print_pass("ISM330DL address found")
        return True
    else:
        print_fail("ISM330DL address not found")
        return False


def test_device_id(sensor):
    print_header("2) Device ID")
    dev_id = sensor.who_am_i()
    print("WHO_AM_I:", hex(dev_id))

    if dev_id == ISM330DL_WHO_AM_I_VALUE:
        print_pass("WHO_AM_I matches 0x{:02X}".format(ISM330DL_WHO_AM_I_VALUE))
        return True
    else:
        print_fail("WHO_AM_I matches expected value", hex(dev_id))
        return False


def test_default_registers(sensor):
    print_header("3) Default driver configuration")
    dump_registers(sensor)

    ctrl3 = sensor._read_u8(REG_CTRL3_C)

    bdu_ok = bool(ctrl3 & CTRL3_C_BDU)
    if_inc_ok = bool(ctrl3 & CTRL3_C_IF_INC)

    if bdu_ok:
        print_pass("BDU enabled")
    else:
        print_fail("BDU enabled")

    if if_inc_ok:
        print_pass("IF_INC enabled")
    else:
        print_fail("IF_INC enabled")

    return bdu_ok and if_inc_ok


def test_soft_reset(sensor):
    print_header("4) Soft reset")
    try:
        sensor.reset()
        sleep(0.05)
        dump_registers(sensor)

        if sensor.who_am_i() == ISM330DL_WHO_AM_I_VALUE:
            print_pass("Soft reset")
            return True
        else:
            print_fail("Soft reset", "WHO_AM_I mismatch after reset")
            return False
    except Exception as err:
        print_fail("Soft reset", err)
        return False


def test_raw_readings(sensor):
    print_header("5) Raw readings")

    try:
        raw_accel = sensor.acceleration_raw()
        raw_gyro = sensor.gyroscope_raw()
        raw_temp = sensor.temperature_raw()

        print("Raw accel :", raw_accel)
        print("Raw gyro  :", raw_gyro)
        print("Raw temp  :", raw_temp)

        accel_ok = raw_accel != (0, 0, 0)
        gyro_ok = raw_gyro != (0, 0, 0)

        if accel_ok:
            print_pass("Accelerometer raw data is not all zero")
        else:
            print_fail("Accelerometer raw data is not all zero")

        if gyro_ok:
            print_pass("Gyroscope raw data is not all zero")
        else:
            print_fail("Gyroscope raw data is not all zero")

        # temp can be close to zero raw around 25°C, so just reading it is enough
        print_pass("Temperature raw read")

        return accel_ok and gyro_ok

    except Exception as err:
        print_fail("Raw readings", err)
        return False


def test_converted_readings(sensor):
    print_header("6) Converted readings")

    try:
        accel_g = sensor.acceleration_g()
        accel_ms2 = sensor.acceleration_ms2()
        gyro_dps = sensor.gyroscope_dps()
        gyro_rads = sensor.gyroscope_rads()
        temp_c = sensor.temperature_c()

        print("Acceleration [g]      :", accel_g)
        print("Acceleration [m/s²]   :", accel_ms2)
        print("Gyroscope [dps]       :", gyro_dps)
        print("Gyroscope [rad/s]     :", gyro_rads)
        print("Temperature [°C]      : {:.2f}".format(temp_c))

        temp_ok = TEMP_MIN <= temp_c <= TEMP_MAX

        # Basic accel sanity check: at rest one axis often sees ~1 g total norm nearby
        ax, ay, az = accel_g
        total_abs = abs(ax) + abs(ay) + abs(az)
        accel_ok = ACCEL_MIN_G <= total_abs <= ACCEL_MAX_G

        if accel_ok:
            print_pass("Acceleration is in a plausible range")
        else:
            print_fail("Acceleration is in a plausible range", total_abs)

        if temp_ok:
            print_pass("Temperature is in a valid range")
        else:
            print_fail("Temperature is in a valid range", temp_c)

        return accel_ok and temp_ok

    except Exception as err:
        print_fail("Converted readings", err)
        return False


def test_configuration_change(sensor):
    print_header("7) Configuration change")

    try:
        sensor.configure_accel(ACCEL_ODR_104HZ, ACCEL_FS_4G)
        sensor.configure_gyro(GYRO_ODR_104HZ, GYRO_FS_500DPS)
        sleep(0.1)

        ctrl1_xl = sensor._read_u8(REG_CTRL1_XL)
        ctrl2_g = sensor._read_u8(REG_CTRL2_G)

        print("CTRL1_XL = 0x{:02X}".format(ctrl1_xl))
        print("CTRL2_G  = 0x{:02X}".format(ctrl2_g))
        print("Accel scale =", sensor._accel_scale, "g")
        print("Gyro scale  =", sensor._gyro_scale, "dps")

        accel_ok = sensor._accel_scale == ACCEL_FS_4G
        gyro_ok = sensor._gyro_scale == GYRO_FS_500DPS

        if accel_ok:
            print_pass("Accelerometer configuration updated")
        else:
            print_fail("Accelerometer configuration updated")

        if gyro_ok:
            print_pass("Gyroscope configuration updated")
        else:
            print_fail("Gyroscope configuration updated")

        # Restore default config
        sensor.configure_accel(ACCEL_ODR_104HZ, ACCEL_FS_2G)
        sensor.configure_gyro(GYRO_ODR_104HZ, GYRO_FS_250DPS)

        return accel_ok and gyro_ok

    except Exception as err:
        print_fail("Configuration change", err)
        return False


def test_status_flags(sensor):
    print_header("8) STATUS helpers")

    try:
        sleep(0.1)

        status = sensor.status()

        print("STATUS =", status)

        accel_ready = status["accel_ready"]
        gyro_ready = status["gyro_ready"]
        temp_ready = status["temp_ready"]

        print("accel_ready =", accel_ready)
        print("gyro_ready  =", gyro_ready)
        print("temp_ready  =", temp_ready)

        if accel_ready or gyro_ready or temp_ready:
            print_pass("STATUS helper methods")
            return True
        else:
            print_fail("STATUS helper methods")
            return False

    except Exception as err:
        print_fail("STATUS helper methods", err)
        return False


def test_live_readings(sensor, samples=5):
    print_header("9) Live readings")

    try:
        previous = None
        changed = False

        for i in range(samples):
            accel = sensor.acceleration_g()
            gyro = sensor.gyroscope_dps()
            temp = sensor.temperature_c()

            print(
                "#{:d}  A=({:+.3f}, {:+.3f}, {:+.3f}) g   "
                "G=({:+.3f}, {:+.3f}, {:+.3f}) dps   "
                "T={:.2f} °C".format(
                    i + 1,
                    accel[0], accel[1], accel[2],
                    gyro[0], gyro[1], gyro[2],
                    temp,
                )
            )

            current = (accel, gyro, temp)

            if previous is not None and current != previous:
                changed = True

            previous = current
            sleep(0.5)

        if changed:
            print_pass("Live readings change over time")
            return True
        else:
            print_fail("Live readings change over time", "values stayed identical")
            return False

    except Exception as err:
        print_fail("Live readings", err)
        return False


def test_power_down(sensor):
    print_header("10) Power down")

    try:
        sensor.power_down()
        sleep(0.05)

        ctrl1_xl = sensor._read_u8(REG_CTRL1_XL)
        ctrl2_g = sensor._read_u8(REG_CTRL2_G)

        print("CTRL1_XL after power_down = 0x{:02X}".format(ctrl1_xl))
        print("CTRL2_G  after power_down = 0x{:02X}".format(ctrl2_g))

        accel_ok = ctrl1_xl == 0x00
        gyro_ok = ctrl2_g == 0x00

        if accel_ok:
            print_pass("Accelerometer powered down")
        else:
            print_fail("Accelerometer powered down", hex(ctrl1_xl))

        if gyro_ok:
            print_pass("Gyroscope powered down")
        else:
            print_fail("Gyroscope powered down", hex(ctrl2_g))

        return accel_ok and gyro_ok

    except Exception as err:
        print_fail("Power down", err)
        return False


def main():
    print_header("ISM330DL full driver test")

    i2c = I2C(1)  # Update bus number if needed

    if not test_i2c_scan(i2c):
        print()
        print("Stop: sensor not found on I2C bus.")
        return

    try:
        sensor = ISM330DL(i2c)
        print_pass("Driver init")
    except Exception as err:
        print_fail("Driver init", err)
        return

    results = []

    results.append(test_device_id(sensor))
    results.append(test_default_registers(sensor))
    results.append(test_soft_reset(sensor))

    # Reconfigure after reset for the following tests
    try:
        sensor.configure_accel(ACCEL_ODR_104HZ, ACCEL_FS_2G)
        sensor.configure_gyro(GYRO_ODR_104HZ, GYRO_FS_250DPS)
        sleep(0.1)
    except Exception as err:
        print_fail("Post-reset reconfiguration", err)
        return

    results.append(test_raw_readings(sensor))
    results.append(test_converted_readings(sensor))
    results.append(test_configuration_change(sensor))
    results.append(test_status_flags(sensor))
    results.append(test_live_readings(sensor, samples=5))
    results.append(test_power_down(sensor))

    print_header("Final result")

    passed = sum(1 for x in results if x)
    total = len(results)

    print("Passed: {}/{}".format(passed, total))

    if passed == total:
        print("All tests passed.")
    else:
        print("Some tests failed.")


main()
