from steami.const import Function
from steami.handle import NAN, Handle


class Humidity(Handle):
    """Relative humidity in %: WSEN-HIDS on V1a/V1b, BME280 on V1c.

    Creating it touches no hardware.
    """

    _NOUN = "humidity sensor"

    def __init__(self):
        super().__init__(Function.HUMIDITY)

    def read(self):
        """Relative humidity in %; nan when unavailable. Calls begin() on first use."""
        return self._read(NAN, "humidity")
