"""Tests of FakeSPI, the recording SPI bus of the display driver tests."""

from tests.fake_machine import FakePin, FakeSPI


def test_write_records_bytes_and_pin_levels():
    dc = FakePin("DC")
    cs = FakePin("CS")
    spi = FakeSPI(1, dc=dc, cs=cs)
    dc.value(0)
    spi.write(bytearray([0x2A]))
    dc.value(1)
    cs.value(1)
    spi.write(memoryview(b"\x00\x01\x02")[1:])
    assert spi.writes == [(0, 0, b"\x2a"), (1, 1, b"\x01\x02")]


def test_init_arguments_are_recorded():
    spi = FakeSPI(1, baudrate=1_000_000)
    spi.init(baudrate=16_000_000, polarity=0, phase=0)
    assert spi.inits == [
        {"baudrate": 1_000_000},
        {"baudrate": 16_000_000, "polarity": 0, "phase": 0},
    ]


def test_commands_group_data_after_each_command_byte():
    dc = FakePin("DC")
    spi = FakeSPI(dc=dc)
    dc.value(0)
    spi.write(b"\x11")
    spi.write(b"\x2a")
    dc.value(1)
    spi.write(b"\x00\x00")
    spi.write(b"\x00\xef")
    assert spi.commands() == [(0x11, b""), (0x2A, b"\x00\x00\x00\xef")]


def test_clear_forgets_writes_and_inits():
    spi = FakeSPI()
    spi.init(baudrate=1)
    spi.write(b"\x00")
    spi.clear()
    assert spi.writes == []
    assert spi.inits == []


def test_pin_init_accepts_an_initial_value():
    pin = FakePin("CS")
    pin.init(pin.OUT, value=1)
    assert pin.value() == 1
