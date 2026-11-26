from math import isnan

from steami.const import Function
from steami.handle import NAN, Handle


class Pressure(Handle):
    """Air pressure in hPa: WSEN-PADS on V1a/V1b, BME280 on V1c.

    Creating it touches no hardware.
    """

    _NOUN = "pressure sensor"

    def __init__(self):
        super().__init__(Function.PRESSURE)

    def read(self):
        """Pressure in hPa; nan when unavailable. Calls begin() on first use."""
        return self._read(NAN, "pressure_hpa")

    def altitude(self, sea_level_hpa=1013.25):
        """Altitude in metres from read() and the sea-level pressure; nan when unavailable.

        The same formula on every release, as the BME280 driver.
        """
        pressure = self.read()
        if isnan(pressure) or sea_level_hpa <= 0:
            return NAN
        return 44330.0 * (1.0 - (pressure / sea_level_hpa) ** 0.1903)
