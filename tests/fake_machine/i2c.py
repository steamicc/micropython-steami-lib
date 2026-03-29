"""Fake I2C bus for testing drivers without hardware."""


class FakeI2C:
    """Simulates a MicroPython I2C bus with pre-loaded register values.

    Args:
        bus_id: optional I2C bus identifier (ignored, accepted for
                MicroPython I2C constructor compatibility).
        registers: dict mapping register addresses to bytes values.
                   Single-byte registers can use int values.
        address: expected I2C device address for validation.
    """

    def __init__(self, bus_id=None, *, registers=None, address=None, **kwargs):
        self._registers = {}
        self._sequences = {}
        self._address = address
        self._write_log = []
        self._read_log = []

        if registers:
            for reg, value in registers.items():
                if isinstance(value, int):
                    self._registers[reg] = bytes([value])
                else:
                    self._registers[reg] = bytes(value)

    def readfrom_mem(self, addr, reg, nbytes, *, addrsize=8):
        self._check_address(addr)
        self._read_log.append(reg)
        seq = self._sequences.get(reg)
        if seq:
            data = seq.pop(0)
            if not seq:
                del self._sequences[reg]
            return data[:nbytes]
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

    def readfrom(self, addr, nbytes, stop=True):
        self._check_address(addr)
        return b"\x00" * nbytes

    def writeto(self, addr, buf, stop=True):
        self._check_address(addr)
        self._write_log.append((None, bytes(buf)))

    def writevto(self, addr, bufs, stop=True):
        self._check_address(addr)
        data = b"".join(bytes(b) for b in bufs)
        self._write_log.append((None, data))

    def scan(self):
        if self._address is not None:
            return [self._address]
        return []

    def get_write_log(self):
        """Return list of (register, data) tuples written."""
        return list(self._write_log)

    def clear_write_log(self):
        self._write_log.clear()

    def get_read_log(self):
        """Return list of register addresses read."""
        return list(self._read_log)

    def clear_read_log(self):
        self._read_log.clear()

    def set_register_sequence(self, reg, values):
        """Set a sequence of values for a register.

        Each read pops the next value from the list. When the list is
        exhausted, reads fall back to the static register value.

        Args:
            reg: register address.
            values: list of bytes values to return on successive reads.
        """
        self._sequences[reg] = [bytes(v) if not isinstance(v, bytes) else v for v in values]

    def _check_address(self, addr):
        if self._address is not None and addr != self._address:
            raise OSError("I2C device not found at 0x{:02X}".format(addr))
