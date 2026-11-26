import math

from steami.const import Function, Status, Vector
from steami.handle import NAN, Handle

_ABSENT = Vector(NAN, NAN, NAN)


class Accelerometer(Handle):
    """Acceleration in g: ISM330DL, on every release. Screen up and flat reads z of about -1.

    Shares the chip with Gyroscope. Creating it touches no hardware.
    """

    _NOUN = "accelerometer"
    _HINT = "Check the board or try another one."
    _FALLBACK = "read() will return NAN."

    def __init__(self):
        super().__init__(Function.ACCELEROMETER)

    def begin(self):
        """Find the chip and set the +-8 g range at 104 Hz on it. True when it answered.

        The range is set on the shared ISM330DL, so is_shaken() can see more
        than 2 g; code that uses Steami.ism330dl() sees that range too.
        """
        if self._status != Status.NOT_STARTED:
            return super().begin()
        ok = super().begin()
        if ok:
            from ism330dl.const import ACCEL_FS_8G, ACCEL_ODR_104HZ

            self._read(None, "configure_accel", ACCEL_ODR_104HZ, ACCEL_FS_8G)
        return ok

    def read(self):
        """Vector(x, y, z) in g, calibration offset included; all nan when unavailable.

        Calls begin() on first use.
        """
        return self._read(_ABSENT, lambda driver: Vector(*driver.acceleration_g()))

    def x(self):
        return self.read().x

    def y(self):
        return self.read().y

    def z(self):
        return self.read().z

    def strength(self):
        """Norm of read() in g; nan when unavailable."""
        x, y, z = self.read()
        return math.sqrt(x * x + y * y + z * z)

    def is_shaken(self, threshold_g=2):
        """True when strength() is above threshold_g."""
        return self.strength() > threshold_g
