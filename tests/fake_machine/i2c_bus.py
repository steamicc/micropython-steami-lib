"""Fake I2C bus holding several devices, for testing board-level code."""

import errno


class FakeI2CBus:
    """Simulates a MicroPython I2C bus with several devices.

    Args:
        devices: dict mapping a 7-bit address to that device's registers
                 (a dict of register address to bytes, or to an int for
                 a single-byte register). Any other address raises
                 OSError(ENODEV), as on the board.
    """

    def __init__(self, devices):
        self._devices = {}
        for addr, registers in devices.items():
            self._devices[addr] = {
                reg: bytes([v]) if isinstance(v, int) else bytes(v)
                for reg, v in registers.items()
            }
        self._sequences = {}
        self._write_log = []

    def _device(self, addr):
        try:
            return self._devices[addr]
        except KeyError:
            raise OSError(errno.ENODEV, "I2C device not found at 0x{:02X}".format(addr)) from None

    def _next(self, addr, reg, nbytes):
        registers = self._device(addr)
        seq = self._sequences.get((addr, reg))
        if seq:
            data = seq.pop(0)
            if not seq:
                del self._sequences[(addr, reg)]
            return data
        return registers.get(reg, b"\x00" * nbytes)

    def readfrom_mem(self, addr, reg, nbytes, *, addrsize=8):
        return self._next(addr, reg, nbytes)[:nbytes]

    def readfrom_mem_into(self, addr, reg, buf, *, addrsize=8):
        data = self._next(addr, reg, len(buf))
        for i in range(len(buf)):
            buf[i] = data[i] if i < len(data) else 0

    def writeto_mem(self, addr, reg, buf, *, addrsize=8):
        self._device(addr)[reg] = bytes(buf)
        self._write_log.append((addr, reg, bytes(buf)))

    def readfrom(self, addr, nbytes, stop=True):
        self._device(addr)
        return b"\x00" * nbytes

    def writeto(self, addr, buf, stop=True):
        self._device(addr)
        self._write_log.append((addr, None, bytes(buf)))

    def writevto(self, addr, bufs, stop=True):
        self._device(addr)
        self._write_log.append((addr, None, b"".join(bytes(b) for b in bufs)))

    def scan(self):
        return sorted(self._devices)

    def get_write_log(self):
        """Return list of (address, register, data) tuples written."""
        return list(self._write_log)

    def clear_write_log(self):
        self._write_log.clear()

    def set_register_sequence(self, addr, reg, values):
        """Make successive reads of a register return the given values.

        When the list is exhausted, reads fall back to the static value.
        """
        self._sequences[(addr, reg)] = [bytes(v) for v in values]
