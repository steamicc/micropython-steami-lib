import math

from steami.const import (
    MAG_CAL_MAX_SAMPLES,
    MAG_CAL_SAMPLE_DELAY_MS,
    MAG_CAL_SAMPLES_PER_SECOND,
    Function,
    Vector,
)
from steami.handle import NAN, Handle

_ABSENT = Vector(NAN, NAN, NAN)
_UT_PER_LSB = 0.15  # 1.5 mG/LSB


def calibrate_minmax(driver, seconds):
    """Min/max calibration of a LIS2MDL driver over `seconds`, kept in the driver.

    Nothing is written to the config zone. Does nothing for 0 seconds: with no
    sample the min/max would wipe the offsets and scales.
    """
    if seconds <= 0:
        return
    samples = min(int(seconds * MAG_CAL_SAMPLES_PER_SECOND), MAG_CAL_MAX_SAMPLES)
    driver.calibrate_minmax_3d(samples, MAG_CAL_SAMPLE_DELAY_MS)


def _field_ut(driver):
    # The offset is in LSB, as the drivers and the config zone keep it.
    x, y, z = driver.magnetic_field()
    return Vector(
        (x - driver.x_off) * _UT_PER_LSB,
        (y - driver.y_off) * _UT_PER_LSB,
        (z - driver.z_off) * _UT_PER_LSB,
    )


class Magnetometer(Handle):
    """Magnetic field in microtesla: LIS2MDL, on every release.

    Shares the chip with Compass. Creating it touches no hardware.
    """

    _NOUN = "magnetometer"
    _FALLBACK = "read() will return NAN."

    def __init__(self):
        super().__init__(Function.MAGNETOMETER)

    def read(self):
        """Vector(x, y, z) in uT, offset removed; all nan when unavailable.

        Calls begin() on first use.
        """
        return self._read(_ABSENT, _field_ut)

    def x(self):
        return self.read().x

    def y(self):
        return self.read().y

    def z(self):
        return self.read().z

    def strength(self):
        """Norm of read() in uT; nan when unavailable."""
        x, y, z = self.read()
        return math.sqrt(x * x + y * y + z * z)

    def calibrate(self, seconds=12):
        """Min/max calibration: turn the board in every direction meanwhile.

        Blocks for `seconds`. The result stays in the driver (not in the config
        zone) until the next reset. Does nothing when unavailable or for 0.
        """
        self._read(None, calibrate_minmax, seconds)
