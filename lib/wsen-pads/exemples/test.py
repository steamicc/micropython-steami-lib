from machine import I2C, Pin
from time import sleep
from wsen_pads import WSEN_PADS
from wsen_pads.const import (
    ODR_1_HZ,
    ODR_10_HZ,
    REG_CTRL_1,
    REG_CTRL_2,
    REG_STATUS,
    REG_INT_SOURCE,
)

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
    ctrl1 = sensor._read_u8(REG_CTRL_1)
    ctrl2 = sensor._read_u8(REG_CTRL_2)
    status = sensor._read_u8(REG_STATUS)
    int_source = sensor._read_u8(REG_INT_SOURCE)

    print("CTRL_1     = 0x{:02X}".format(ctrl1))
    print("CTRL_2     = 0x{:02X}".format(ctrl2))
    print("STATUS     = 0x{:02X}".format(status))
    print("INT_SOURCE = 0x{:02X}".format(int_source))


def test_i2c_scan(i2c):
    print_header("1) I2C scan")
    devices = i2c.scan()
    print("I2C devices found:", [hex(x) for x in devices])

    if 0x5C in devices or 0x5D in devices:
        print_pass("WSEN-PADS address found")
        return True
    else:
        print_fail("WSEN-PADS address found")
        return False


def test_device_id(sensor):
    print_header("2) Device ID")
    dev_id = sensor.device_id()
    print("Device ID:", hex(dev_id))

    if dev_id == 0xB3:
        print_pass("Device ID matches 0xB3")
        return True
    else:
        print_fail("Device ID matches 0xB3", hex(dev_id))
        return False


def test_default_registers(sensor):
    print_header("3) Default driver configuration")
    dump_registers(sensor)

    ctrl1 = sensor._read_u8(REG_CTRL_1)
    ctrl2 = sensor._read_u8(REG_CTRL_2)

    # BDU should be enabled by the driver
    bdu_ok = bool(ctrl1 & 0x02)

    # IF_ADD_INC should be enabled by the driver
    if_add_inc_ok = bool(ctrl2 & 0x10)

    if bdu_ok:
        print_pass("BDU enabled")
    else:
        print_fail("BDU enabled")

    if if_add_inc_ok:
        print_pass("IF_ADD_INC enabled")
    else:
        print_fail("IF_ADD_INC enabled")

    return bdu_ok and if_add_inc_ok


def test_soft_reset(sensor):
    print_header("4) Soft reset")
    try:
        sensor.soft_reset()
        sleep(0.05)
        dump_registers(sensor)

        if sensor.device_id() == 0xB3:
            print_pass("Soft reset")
            return True
        else:
            print_fail("Soft reset", "device ID mismatch after reset")
            return False
    except Exception as err:
        print_fail("Soft reset", err)
        return False


def test_reboot(sensor):
    print_header("5) Reboot")
    try:
        sensor.reboot()
        sleep(0.05)
        dump_registers(sensor)

        if sensor.device_id() == 0xB3:
            print_pass("Reboot")
            return True
        else:
            print_fail("Reboot", "device ID mismatch after reboot")
            return False
    except Exception as err:
        print_fail("Reboot", err)
        return False


def test_one_shot(sensor):
    print_header("6) One-shot read")

    try:
        pressure_hpa, temperature_c = sensor.read_one_shot()

        raw_p = sensor.pressure_raw()
        raw_t = sensor.temperature_raw()
        status = sensor.status()

        print("Raw pressure    :", raw_p)
        print("Raw temperature :", raw_t)
        print("Pressure        : {:.2f} hPa".format(pressure_hpa))
        print("Temperature     : {:.2f} °C".format(temperature_c))
        print("STATUS          : 0x{:02X}".format(status))

        # Basic sanity checks
        MIN_PRESSURE = 260.0
        MAX_PRESSURE = 1260.0
        MIN_TEMPERATURE = -40.0
        MAX_TEMPERATURE = 85.0
        pressure_ok = MIN_PRESSURE <= pressure_hpa <= MAX_PRESSURE
        temperature_ok = MIN_TEMPERATURE <= temperature_c <= MAX_TEMPERATURE
        raw_ok = not (raw_p == 0 and raw_t == 0)

        if raw_ok:
            print_pass("Raw data is not all zero")
        else:
            print_fail("Raw data is not all zero")

        if pressure_ok:
            print_pass("Pressure is in a valid range")
        else:
            print_fail("Pressure is in a valid range", pressure_hpa)

        if temperature_ok:
            print_pass("Temperature is in a valid range")
        else:
            print_fail("Temperature is in a valid range", temperature_c)

        return raw_ok and pressure_ok and temperature_ok

    except Exception as err:
        print_fail("One-shot read", err)
        return False


def test_continuous_mode(sensor, odr, label, wait_s=2):
    print_header("7) Continuous mode - {}".format(label))

    try:
        sensor.set_continuous(odr=odr)
        print("Waiting {} second(s) for fresh samples...".format(wait_s))
        sleep(wait_s)

        ok = True

        for i in range(5):
            pressure_hpa = sensor.pressure()
            temperature_c = sensor.temperature()
            raw_p = sensor.pressure_raw()
            raw_t = sensor.temperature_raw()
            status = sensor.status()

            print(
                "#{:d}  P={:.2f} hPa  T={:.2f} °C  rawP={}  rawT={}  STATUS=0x{:02X}".format(
                    i + 1,
                    pressure_hpa,
                    temperature_c,
                    raw_p,
                    raw_t,
                    status,
                )
            )

            if raw_p == 0 and raw_t == 0:
                ok = False

            sleep(0.5)

        sensor.power_down()

        if ok:
            print_pass("Continuous mode - {}".format(label))
        else:
            print_fail("Continuous mode - {}".format(label), "raw data stayed at zero")

        return ok

    except Exception as err:
        print_fail("Continuous mode - {}".format(label), err)
        return False


def test_status_flags(sensor):
    print_header("8) STATUS helpers")

    try:
        sensor.set_continuous(odr=ODR_1_HZ)
        sleep(1.5)

        status = sensor.status()
        p_avail = sensor.pressure_available()
        t_avail = sensor.temperature_available()
        ready = sensor.is_ready()

        print("STATUS                = 0x{:02X}".format(status))
        print("pressure_available()  =", p_avail)
        print("temperature_available() =", t_avail)
        print("is_ready()            =", ready)

        sensor.power_down()

        if p_avail or t_avail or ready:
            print_pass("STATUS helper methods")
            return True
        else:
            print_fail("STATUS helper methods")
            return False

    except Exception as err:
        print_fail("STATUS helper methods", err)
        return False


def main():
    print_header("WSEN-PADS full driver test")

    i2c = I2C(1)

    if not test_i2c_scan(i2c):
        print()
        print("Stop: sensor not found on I2C bus.")
        return

    try:
        sensor = WSEN_PADS(i2c)
    except Exception as err:
        print_fail("Driver init", err)
        return

    results = []

    results.append(test_device_id(sensor))
    results.append(test_default_registers(sensor))
    results.append(test_soft_reset(sensor))
    results.append(test_reboot(sensor))
    results.append(test_one_shot(sensor))
    results.append(test_continuous_mode(sensor, ODR_1_HZ, "1 Hz", wait_s=2))
    results.append(test_continuous_mode(sensor, ODR_10_HZ, "10 Hz", wait_s=1))
    results.append(test_status_flags(sensor))

    print_header("Final result")

    passed = sum(1 for x in results if x)
    total = len(results)

    print("Passed: {}/{}".format(passed, total))

    if passed == total:
        print("All tests passed.")
    else:
        print("Some tests failed.")


main()