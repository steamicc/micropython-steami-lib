"""Fake I2C bus for testing drivers without hardware."""


class FakeI2C:
    """Simulates a MicroPython I2C bus with pre-loaded register values.

    Args:
        registers: dict mapping register addresses to bytes values.
                   Single-byte registers can use int values.
        address: expected I2C device address for validation.
    """

    def __init__(self, bus_id=None, *, registers=None, address=None, **kwargs):
        self._registers = {}
        self._address = address
        self._write_log = []

        if registers:
            for reg, value in registers.items():
                if isinstance(value, int):
                    self._registers[reg] = bytes([value])
                else:
                    self._registers[reg] = bytes(value)

    def readfrom_mem(self, addr, reg, nbytes, *, addrsize=8):
        self._check_address(addr)
        data = self._registers.get(reg, b"\x00" * nbytes)
        return data[:nbytes]

    def readfrom_mem_into(self, addr, reg, buf, *, addrsize=8):
        self._check_address(addr)
        data = self._registers.get(reg, b"\x00" * len(buf))
        for i in range(len(buf)):
            buf[i] = data[i] if i < len(data) else 0

    def writeto_mem(self, addr, reg, buf, *, addrsize=8):
        self._check_address(addr)
        self._registers[reg] = bytes(buf)
        self._write_log.append((reg, bytes(buf)))

    def scan(self):
        if self._address is not None:
            return [self._address]
        return []

    def get_write_log(self):
        """Return list of (register, data) tuples written."""
        return list(self._write_log)

    def clear_write_log(self):
        self._write_log.clear()

    def _check_address(self, addr):
        if self._address is not None and addr != self._address:
            raise OSError("I2C device not found at 0x{:02X}".format(addr))
