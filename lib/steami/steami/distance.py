from steami.const import Function, Status
from steami.handle import NAN, Handle


class Distance(Handle):
    """Distance to the nearest object in front of the board: VL53L1X, on every release.

    Creating it touches no hardware.
    """

    _NOUN = "distance sensor"
    _FALLBACK = "read() will return -1."

    def __init__(self):
        super().__init__(Function.DISTANCE)

    def begin(self):
        """Find the sensor and start ranging. True when it answered."""
        if self._status != Status.NOT_STARTED:
            return super().begin()
        ok = super().begin()
        if ok:
            self._read(None, "start_ranging")
        return ok

    def read(self):
        """Distance in millimetres; -1 when unavailable or when no target is seen.

        Calls begin() on first use.
        """
        mm = self._read(0, "read")
        return mm if mm > 0 else -1

    def cm(self):
        """Distance in centimetres; nan when read() gives -1."""
        mm = self.read()
        return NAN if mm < 0 else mm / 10.0
