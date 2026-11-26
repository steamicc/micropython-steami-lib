"""Tests of the multi-device fake I2C bus and the STeaMi chip images."""

import pytest

from tests.fake_machine import FakePin, steami_chips
from tests.fake_machine.i2c_bus import FakeI2CBus
from tests.runner.executor import cleanup_driver, load_driver_mock

# chip -> (driver dir, module name, class name)
DRIVERS = {
    "BME280": ("bme280", "bme280", "BME280"),
    "WSEN-HIDS": ("wsen-hids", "wsen_hids", "WSEN_HIDS"),
    "WSEN-PADS": ("wsen-pads", "wsen_pads", "WSEN_PADS"),
    "APDS-9960": ("apds9960", "apds9960", "uAPDS9960"),
    "VL53L1X": ("vl53l1x", "vl53l1x", "VL53L1X"),
    "ISM330DL": ("ism330dl", "ism330dl", "ISM330DL"),
    "LIS2MDL": ("lis2mdl", "lis2mdl", "LIS2MDL"),
    "BQ27441": ("bq27441", "bq27441", "BQ27441"),
    "MCP23009E": ("mcp23009e", "mcp23009e", "MCP23009E"),
}

RELEASES = {
    "V1a/V1b": ["WSEN-HIDS", "WSEN-PADS", "APDS-9960", "VL53L1X", "ISM330DL",
                "LIS2MDL", "BQ27441", "MCP23009E"],
    "V1c": ["BME280", "VL53L1X", "ISM330DL", "LIS2MDL", "BQ27441", "MCP23009E"],
}

CASES = [(release, chip) for release, chips in RELEASES.items() for chip in chips]


@pytest.mark.parametrize("release,chip", CASES)
def test_driver_constructs_on_board_mock(release, chip):
    driver_dir, module_name, class_name = DRIVERS[chip]
    bus = steami_chips.board(release)
    module, _ = load_driver_mock(driver_dir, bus, module_name=module_name)
    try:
        kwargs = {"reset_pin": FakePin(0)} if chip == "MCP23009E" else {}
        getattr(module, class_name)(bus, address=steami_chips.ADDRESS[chip], **kwargs)
    finally:
        cleanup_driver(driver_dir, module_name)


@pytest.mark.parametrize("release", RELEASES)
def test_scan_lists_the_chips_of_the_release(release):
    expected = {steami_chips.ADDRESS[c] for c in RELEASES[release]} | {0x3B}
    assert set(steami_chips.board(release).scan()) == expected


def test_missing_chip_is_absent():
    bus = steami_chips.board("V1c", missing=("BME280",))
    assert 0x76 not in bus.scan()
    with pytest.raises(OSError):
        bus.readfrom_mem(0x76, 0xD0, 1)


def test_absent_address_raises_enodev():
    bus = FakeI2CBus({0x10: {0x00: 0x42}})
    with pytest.raises(OSError) as err:
        bus.readfrom_mem(0x11, 0x00, 1)
    assert err.value.args[0] == 19
    with pytest.raises(OSError):
        bus.writeto_mem(0x11, 0x00, b"\x01")
    with pytest.raises(OSError):
        bus.readfrom(0x11, 1)


def test_registers_are_per_device():
    bus = FakeI2CBus({0x10: {0x00: 0x01}, 0x20: {0x00: 0x02}})
    assert bus.readfrom_mem(0x10, 0x00, 1) == b"\x01"
    assert bus.readfrom_mem(0x20, 0x00, 1) == b"\x02"
    bus.writeto_mem(0x20, 0x00, b"\x09")
    assert bus.readfrom_mem(0x10, 0x00, 1) == b"\x01"
    assert bus.readfrom_mem(0x20, 0x00, 1) == b"\x09"
    assert bus.get_write_log() == [(0x20, 0x00, b"\x09")]


def test_sequence_and_into():
    bus = FakeI2CBus({0x10: {0x05: b"\xAA\xBB"}})
    bus.set_register_sequence(0x10, 0x05, [b"\x01\x02", b"\x03\x04"])
    buf = bytearray(2)
    bus.readfrom_mem_into(0x10, 0x05, buf)
    assert bytes(buf) == b"\x01\x02"
    assert bus.readfrom_mem(0x10, 0x05, 2) == b"\x03\x04"
    assert bus.readfrom_mem(0x10, 0x05, 2) == b"\xAA\xBB"


def test_image_is_a_copy():
    image = steami_chips.image("BME280")
    assert image[0xD0] == 0x60
    image[0xD0] = 0
    assert steami_chips.image("BME280")[0xD0] == 0x60
