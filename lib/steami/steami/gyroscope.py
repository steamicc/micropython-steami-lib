from steami.const import Function, Vector
from steami.handle import NAN, Handle

_ABSENT = Vector(NAN, NAN, NAN)


class Gyroscope(Handle):
    """Angular speed in degrees per second: ISM330DL, on every release.

    Shares the chip with Accelerometer. Creating it touches no hardware.
    """

    _NOUN = "gyroscope"
    _FALLBACK = "read() will return NAN."

    def __init__(self):
        super().__init__(Function.GYROSCOPE)

    def read(self):
        """Vector(x, y, z) in dps; all nan when unavailable. Calls begin() on first use."""
        return self._read(_ABSENT, lambda driver: Vector(*driver.gyroscope_dps()))

    def x(self):
        return self.read().x

    def y(self):
        return self.read().y

    def z(self):
        return self.read().z
