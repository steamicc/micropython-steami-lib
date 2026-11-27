"""Fake machine module for testing MicroPython drivers on CPython."""

from tests.fake_machine.i2c import FakeI2C
from tests.fake_machine.pin import FakePin
from tests.fake_machine.spi import FakeSPI

__all__ = ["FakeI2C", "FakePin", "FakeSPI"]
