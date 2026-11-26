from steami.const import Function
from steami.handle import NAN, Handle


class Temperature(Handle):
    """Temperature in degrees Celsius: WSEN-HIDS, then WSEN-PADS on V1a/V1b, BME280 on V1c.

    Creating it touches no hardware.
    """

    _NOUN = "temperature sensor"

    def __init__(self):
        super().__init__(Function.TEMPERATURE)
        self._offset = 0.0

    def read(self):
        """Degrees Celsius, calibration and offset included; nan when unavailable.

        Calls begin() on first use.
        """
        return self._read(NAN, "temperature") + self._offset

    def set_offset(self, offset_c):
        """Add offset_c to every read() of this object; the shared driver is not changed."""
        self._offset = float(offset_c)
