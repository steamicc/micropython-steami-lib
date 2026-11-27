"""Fake SPI bus for testing display drivers without hardware."""


class FakeSPI:
    """Simulates a MicroPython SPI bus and records what is sent.

    Each write() is stored in ``writes`` as ``(dc, cs, data)``: the levels of
    the D/C and CS pins at the time of the write (None when no pin is
    attached) and the bytes sent. Each init() stores its keyword arguments in
    ``inits``. Attach the pins at creation or later (``spi.dc = pin``).
    """

    MSB = 0
    LSB = 1

    def __init__(self, bus_id=None, *, dc=None, cs=None, **kwargs):
        self.bus_id = bus_id
        self.dc = dc
        self.cs = cs
        self.writes = []
        self.inits = []
        if kwargs:
            self.init(**kwargs)

    def init(self, **kwargs):
        self.inits.append(kwargs)

    def deinit(self):
        pass

    def write(self, buf):
        dc = None if self.dc is None else self.dc.value()
        cs = None if self.cs is None else self.cs.value()
        self.writes.append((dc, cs, bytes(buf)))

    def clear(self):
        """Forget the recorded writes and init() calls."""
        self.writes = []
        self.inits = []

    def commands(self):
        """Return the writes as ``[(command, data), ...]``.

        Each byte sent with D/C low is a command; the bytes sent with D/C
        high are the data of the command before them.
        """
        result = []
        for dc, _cs, data in self.writes:
            if dc:
                cmd, params = result[-1]
                result[-1] = (cmd, params + data)
            else:
                result.extend((byte, b"") for byte in data)
        return result
