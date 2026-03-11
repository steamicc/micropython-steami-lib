"""Fake machine module for testing MicroPython drivers on CPython."""

from tests.fake_machine.i2c import FakeI2C
from tests.fake_machine.pin import FakePin

__all__ = ["FakeI2C", "FakePin"]
