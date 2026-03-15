from machine import I2C
from time import sleep, sleep_ms

from wsen_hids import WSEN_HIDS
from wsen_hids.const import *

# ---------------------------------------------------------------------
# Update these pins and bus number to match your board
# ---------------------------------------------------------------------
MIN_HUMIDITY = 0.0
MAX_HUMIDITY = 100.0
MIN_TEMPERATURE = -40.0
MAX_TEMPERATURE = 120.0

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


def read_reg(sensor, reg):
    return sensor._read_reg(reg)


def dump_registers(sensor):
    print("DEVICE_ID = 0x{:02X}".format(read_reg(sensor, REG_DEVICE_ID)))
    print("AV_CONF   = 0x{:02X}".format(read_reg(sensor, REG_AV_CONF)))
    print("CTRL_1    = 0x{:02X}".format(read_reg(sensor, REG_CTRL_1)))
    print("CTRL_2    = 0x{:02X}".format(read_reg(sensor, REG_CTRL_2)))
    print("CTRL_3    = 0x{:02X}".format(read_reg(sensor, REG_CTRL_3)))
    print("STATUS    = 0x{:02X}".format(read_reg(sensor, REG_STATUS)))
    print("H_OUT_L   = 0x{:02X}".format(read_reg(sensor, REG_H_OUT_L)))
    print("H_OUT_H   = 0x{:02X}".format(read_reg(sensor, REG_H_OUT_H)))
    print("T_OUT_L   = 0x{:02X}".format(read_reg(sensor, REG_T_OUT_L)))
    print("T_OUT_H   = 0x{:02X}".format(read_reg(sensor, REG_T_OUT_H)))


def test_i2c_scan(i2c):
    print_header("1) I2C scan")
    devices = i2c.scan()
    print("I2C devices found:", [hex(x) for x in devices])

    if WSEN_HIDS_I2C_ADDRESS in devices:
        print_pass("WSEN-HIDS address found")
        return True
    else:
        print_fail("WSEN-HIDS address found")
        return False


def test_device_id(sensor):
    print_header("2) Device ID")

    try:
        dev_id = sensor.device_id()
        print("Device ID:", hex(dev_id))

        if dev_id == WSEN_HIDS_DEVICE_ID:
            print_pass("Device ID matches 0x{:02X}".format(WSEN_HIDS_DEVICE_ID))
            return True
        else:
            print_fail(
                "Device ID matches 0x{:02X}".format(WSEN_HIDS_DEVICE_ID),
                hex(dev_id),
            )
            return False

    except Exception as err:
        print_fail("Device ID", err)
        return False


def test_default_registers(sensor):
    print_header("3) Default driver configuration")
    try:
        dump_registers(sensor)

        ctrl1 = read_reg(sensor, REG_CTRL_1)
        av_conf = read_reg(sensor, REG_AV_CONF)

        bdu_ok = bool(ctrl1 & CTRL_1_BDU)

        # Driver defaults proposed:
        # avg_t = AVG_16, avg_h = AVG_16
        avg_t = (av_conf >> 3) & 0x07
        avg_h = av_conf & 0x07
        avg_ok = (avg_t == AVG_16) and (avg_h == AVG_16)

        if bdu_ok:
            print_pass("BDU enabled")
        else:
            print_fail("BDU enabled")

        if avg_ok:
            print_pass("Default averaging configuration")
        else:
            print_fail(
                "Default averaging configuration",
                "AVG_T={}, AVG_H={}".format(avg_t, avg_h),
            )

        return bdu_ok and avg_ok

    except Exception as err:
        print_fail("Default driver configuration", err)
        return False


def test_reboot(sensor):
    print_header("4) Reboot memory")
    try:
        sensor.reboot()
        sleep(0.05)
        dump_registers(sensor)

        if sensor.device_id() == WSEN_HIDS_DEVICE_ID:
            print_pass("Reboot memory")
            return True
        else:
            print_fail("Reboot memory", "device ID mismatch after reboot")
            return False

    except Exception as err:
        print_fail("Reboot memory", err)
        return False


def test_one_shot(sensor):
    print_header("5) One-shot read")

    try:
        humidity_rh, temperature_c = sensor.read_one_shot(timeout_ms=500)

        status = sensor.status()
        h_ready = sensor.humidity_ready()
        t_ready = sensor.temperature_ready()
        ready = sensor.data_ready()

        print("Humidity        : {:.2f} %RH".format(humidity_rh))
        print("Temperature     : {:.2f} °C".format(temperature_c))
        print("STATUS          : 0x{:02X}".format(status))
        print("humidity_ready  :", h_ready)
        print("temperature_ready:", t_ready)
        print("data_ready      :", ready)

        humidity_ok = MIN_HUMIDITY <= humidity_rh <= MAX_HUMIDITY
        temperature_ok = MIN_TEMPERATURE <= temperature_c <= MAX_TEMPERATURE

        if humidity_ok:
            print_pass("Humidity is in a valid range")
        else:
            print_fail("Humidity is in a valid range", humidity_rh)

        if temperature_ok:
            print_pass("Temperature is in a valid range")
        else:
            print_fail("Temperature is in a valid range", temperature_c)

        return humidity_ok and temperature_ok

    except Exception as err:
        print_fail("One-shot read", err)
        return False


def test_one_shot_loop(sensor, count=5, delay_s=1):
    print_header("6) One-shot loop")

    ok = True

    try:
        for i in range(count):
            humidity_rh, temperature_c = sensor.read_one_shot(timeout_ms=500)

            print(
                "#{:d}  H={:.2f} %RH  T={:.2f} °C".format(
                    i + 1,
                    humidity_rh,
                    temperature_c,
                )
            )

            if not (MIN_HUMIDITY <= humidity_rh <= MAX_HUMIDITY):
                ok = False

            sleep(delay_s)

        if ok:
            print_pass("One-shot loop")
        else:
            print_fail("One-shot loop", "invalid humidity value detected")

        return ok

    except Exception as err:
        print_fail("One-shot loop", err)
        return False


def test_continuous_mode(sensor, odr, label, wait_ms=1500, loops=5, delay_s=0.5):
    print_header("7) Continuous mode - {}".format(label))

    try:
        sensor.set_continuous_mode(odr=odr)

        ctrl1 = read_reg(sensor, REG_CTRL_1)
        pd_ok = bool(ctrl1 & CTRL_1_PD)
        odr_ok = (ctrl1 & CTRL_1_ODR_MASK) == odr

        print("CTRL_1 after set_continuous_mode = 0x{:02X}".format(ctrl1))

        if pd_ok:
            print_pass("PD bit set")
        else:
            print_fail("PD bit set")

        if odr_ok:
            print_pass("ODR configured correctly")
        else:
            print_fail("ODR configured correctly", "CTRL_1=0x{:02X}".format(ctrl1))

        print("Waiting {} ms for fresh samples...".format(wait_ms))
        sleep_ms(wait_ms)

        ok = pd_ok and odr_ok

        last_h = None
        last_t = None

        for i in range(loops):
            humidity_rh, temperature_c = sensor.read()
            status = sensor.status()

            print(
                "#{:d}  H={:.2f} %RH  T={:.2f} °C  STATUS=0x{:02X}".format(
                    i + 1,
                    humidity_rh,
                    temperature_c,
                    status,
                )
            )

            if not (MIN_HUMIDITY <= humidity_rh <= MAX_HUMIDITY):
                ok = False

            if not (MIN_TEMPERATURE <= temperature_c <= MAX_TEMPERATURE):
                ok = False

            if last_h is not None and abs(humidity_rh - last_h) > 50:
                ok = False

            if last_t is not None and abs(temperature_c - last_t) > 30:
                ok = False

            last_h = humidity_rh
            last_t = temperature_c

            sleep(delay_s)

        sensor.set_one_shot_mode()

        if ok:
            print_pass("Continuous mode - {}".format(label))
        else:
            print_fail("Continuous mode - {}".format(label), "invalid sample detected")

        return ok

    except Exception as err:
        print_fail("Continuous mode - {}".format(label), err)
        return False


def test_status_helpers(sensor):
    print_header("8) STATUS helpers")

    try:
        sensor.set_continuous_mode(odr=ODR_1_HZ)
        sleep(1.5)

        status = sensor.status()
        h_avail = sensor.humidity_ready()
        t_avail = sensor.temperature_ready()
        ready = sensor.data_ready()

        print("STATUS              = 0x{:02X}".format(status))
        print("humidity_ready()    =", h_avail)
        print("temperature_ready() =", t_avail)
        print("data_ready()        =", ready)

        sensor.set_one_shot_mode()

        # At least one indicator must match STATUS
        flags_match = (
            h_avail == bool(status & STATUS_H_DA)
            and t_avail == bool(status & STATUS_T_DA)
        )

        if flags_match:
            print_pass("STATUS helper methods")
            return True
        else:
            print_fail("STATUS helper methods", "helpers do not match STATUS bits")
            return False

    except Exception as err:
        print_fail("STATUS helper methods", err)
        return False


def test_unitary_methods(sensor):
    print_header("9) humidity() and temperature()")

    try:
        sensor.set_continuous_mode(odr=ODR_1_HZ)
        sleep(1.2)

        humidity_rh = sensor.humidity()
        temperature_c = sensor.temperature()

        print("humidity()    = {:.2f} %RH".format(humidity_rh))
        print("temperature() = {:.2f} °C".format(temperature_c))

        sensor.set_one_shot_mode()

        humidity_ok = MIN_HUMIDITY <= humidity_rh <= MAX_HUMIDITY
        temperature_ok = MIN_TEMPERATURE <= temperature_c <= MAX_TEMPERATURE

        if humidity_ok:
            print_pass("humidity() valid")
        else:
            print_fail("humidity() valid", humidity_rh)

        if temperature_ok:
            print_pass("temperature() valid")
        else:
            print_fail("temperature() valid", temperature_c)

        return humidity_ok and temperature_ok

    except Exception as err:
        print_fail("humidity() and temperature()", err)
        return False


def test_heater(sensor):
    print_header("10) Heater control")

    try:
        sensor.enable_heater(True)
        sleep_ms(20)
        ctrl2_on = read_reg(sensor, REG_CTRL_2)
        heater_on_ok = bool(ctrl2_on & CTRL_2_HEATER)

        print("CTRL_2 with heater ON  = 0x{:02X}".format(ctrl2_on))

        sensor.enable_heater(False)
        sleep_ms(20)
        ctrl2_off = read_reg(sensor, REG_CTRL_2)
        heater_off_ok = not bool(ctrl2_off & CTRL_2_HEATER)

        print("CTRL_2 with heater OFF = 0x{:02X}".format(ctrl2_off))

        if heater_on_ok:
            print_pass("Heater enable")
        else:
            print_fail("Heater enable")

        if heater_off_ok:
            print_pass("Heater disable")
        else:
            print_fail("Heater disable")

        return heater_on_ok and heater_off_ok

    except Exception as err:
        print_fail("Heater control", err)
        return False


def test_average_configuration(sensor):
    print_header("11) Average configuration")

    try:
        sensor.set_average(avg_t=AVG_8, avg_h=AVG_4)
        av_conf_1 = read_reg(sensor, REG_AV_CONF)
        avg_t_1 = (av_conf_1 >> 3) & 0x07
        avg_h_1 = av_conf_1 & 0x07

        print("AV_CONF (AVG_T=AVG_8, AVG_H=AVG_4)  = 0x{:02X}".format(av_conf_1))

        ok1 = (avg_t_1 == AVG_8) and (avg_h_1 == AVG_4)

        sensor.set_average(avg_t=AVG_64, avg_h=AVG_32)
        av_conf_2 = read_reg(sensor, REG_AV_CONF)
        avg_t_2 = (av_conf_2 >> 3) & 0x07
        avg_h_2 = av_conf_2 & 0x07

        print("AV_CONF (AVG_T=AVG_64, AVG_H=AVG_32) = 0x{:02X}".format(av_conf_2))

        ok2 = (avg_t_2 == AVG_64) and (avg_h_2 == AVG_32)

        # restore defaults
        sensor.set_average(avg_t=AVG_16, avg_h=AVG_16)

        if ok1:
            print_pass("Average configuration set #1")
        else:
            print_fail("Average configuration set #1")

        if ok2:
            print_pass("Average configuration set #2")
        else:
            print_fail("Average configuration set #2")

        return ok1 and ok2

    except Exception as err:
        print_fail("Average configuration", err)
        return False


def test_register_dump_after_reads(sensor):
    print_header("12) Register dump after measurements")

    try:
        sensor.read_one_shot(timeout_ms=500)
        dump_registers(sensor)
        print_pass("Register dump after measurements")
        return True
    except Exception as err:
        print_fail("Register dump after measurements", err)
        return False


def main():
    print_header("WSEN-HIDS full driver test")

    i2c = I2C(1)

    if not test_i2c_scan(i2c):
        print()
        print("Stop: sensor not found on I2C bus.")
        return

    try:
        sensor = WSEN_HIDS(i2c)
        print_pass("Driver init")
    except Exception as err:
        print_fail("Driver init", err)
        return

    results = []

    results.append(test_device_id(sensor))
    results.append(test_default_registers(sensor))
    results.append(test_reboot(sensor))
    results.append(test_one_shot(sensor))
    results.append(test_one_shot_loop(sensor, count=5, delay_s=1))
    results.append(test_continuous_mode(sensor, ODR_1_HZ, "1 Hz", wait_ms=1500))
    results.append(test_continuous_mode(sensor, ODR_7_HZ, "7 Hz", wait_ms=500))
    results.append(test_continuous_mode(sensor, ODR_12_5_HZ, "12.5 Hz", wait_ms=300))
    results.append(test_status_helpers(sensor))
    results.append(test_unitary_methods(sensor))
    results.append(test_heater(sensor))
    results.append(test_average_configuration(sensor))
    results.append(test_register_dump_after_reads(sensor))

    print_header("Final result")

    passed = sum(1 for x in results if x)
    total = len(results)

    print("Passed: {}/{}".format(passed, total))

    if passed == total:
        print("All tests passed.")
    else:
        print("Some tests failed.")


main()
