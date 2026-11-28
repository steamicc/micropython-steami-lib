import math

from steami.accelerometer import Accelerometer
from steami.const import Function, Status
from steami.handle import NAN, Handle
from steami.magnetometer import calibrate_minmax


class Compass(Handle):
    """Heading of the board held flat: LIS2MDL, on every release.

    Shares the chip with Magnetometer. Creating it touches no hardware.
    """

    _NOUN = "compass"
    _FALLBACK = "heading() will return NAN."

    def __init__(self):
        super().__init__(Function.COMPASS)
        self._declination = None
        self._accelerometer = None

    def begin(self):
        """Find the chip and apply the declination set before. True when it answered."""
        if self._status != Status.NOT_STARTED:
            return super().begin()
        ok = super().begin()
        if ok and self._declination is not None:
            self._read(None, "set_declination", self._declination)
        return ok

    def heading(self):
        """Degrees clockwise from north in [0, 360), screen up and flat; nan when unavailable.

        Calls begin() on first use.
        """
        return self._read(NAN, "heading_flat_only")

    def heading_tilt_compensated(self):
        """As heading(), but corrected with the accelerometer when the board is tilted.

        Equals heading() when flat; nan when either sensor is unavailable.
        Needs the 3D calibration of calibrate() or of the board config; valid
        up to about 60 degrees of tilt. The first call sets the ISM330DL to
        +-8 g at 104 Hz, as Accelerometer does; a missing accelerometer is
        reported under the Accelerometer name.
        """
        if self._accelerometer is None:
            self._accelerometer = Accelerometer()
        a = self._accelerometer.read()
        return self._read(NAN, "heading_with_tilt_compensation", lambda: a)

    def direction(self):
        """ "N", "NE", "E"... for heading(); "" when unavailable."""
        angle = self.heading()
        if math.isnan(angle):
            return ""
        return self._read("", "direction_label", angle)

    def calibrate(self, seconds=12):
        """Min/max calibration: turn the board in every direction meanwhile.

        Blocks for `seconds`. The result stays in the driver (not in the config
        zone) until the next reset. Does nothing when unavailable or for 0.
        """
        self._read(None, calibrate_minmax, seconds)

    def set_declination(self, deg):
        """Magnetic declination in degrees, added to the heading. May be called before begin()."""
        self._declination = deg
        if self._status == Status.OK:
            self._read(None, "set_declination", deg)
