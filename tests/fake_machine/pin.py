"""Fake Pin for testing drivers without hardware."""


class FakePin:
    """Simulates a MicroPython Pin."""

    IN = 0
    OUT = 1
    PULL_UP = 1
    PULL_DOWN = 2

    def __init__(self, pin_id, mode=IN, pull=None):
        self._id = pin_id
        self._mode = mode
        self._pull = pull
        self._value = 0

    def value(self, val=None):
        if val is None:
            return self._value
        self._value = val

    def init(self, mode=IN, pull=None):
        self._mode = mode
        self._pull = pull
