from steami.const import Function
from steami.handle import Handle

_ABSENT = (0, 0, 0)


def _rgb(driver):
    return (driver.red_light(), driver.green_light(), driver.blue_light())


class Color(Handle):
    """Red, green and blue counts: APDS-9960, on V1a and V1b only. A V1c reports E20.

    Shares the chip with Light and Gesture; reading it turns the light engine
    on and leaves the other engines as they are. Creating it touches no hardware.
    """

    _NOUN = "colour sensor"
    _FALLBACK = "read() will return (0, 0, 0)."

    def __init__(self):
        super().__init__(Function.COLOR)

    def read(self):
        """Raw counts as a tuple (r, g, b); (0, 0, 0) when unavailable or when a
        channel cannot be read.

        Calls begin() on first use.
        """
        return self._read(_ABSENT, _rgb)

    def red(self):
        return self.read()[0]

    def green(self):
        return self.read()[1]

    def blue(self):
        return self.read()[2]
