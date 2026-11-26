from steami.const import Function
from steami.handle import Handle


class Light(Handle):
    """Ambient light: APDS-9960, on V1a and V1b only. A V1c reports E20.

    Shares the chip with Color and Gesture; reading it turns the light engine
    on and leaves the other engines as they are. Creating it touches no hardware.
    """

    _NOUN = "light sensor"
    _FALLBACK = "read() will return 0."

    def __init__(self):
        super().__init__(Function.LIGHT)

    def read(self):
        """Raw count of the clear channel; 0 when unavailable.

        Calls begin() on first use.
        """
        return self._read(0, "ambient_light")
