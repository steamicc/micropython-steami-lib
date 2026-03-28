from time import sleep_ms

from daplink_bridge.const import *


class DaplinkBridge(object):
    """Low-level I2C bridge to the STM32F103 DAPLink interface."""

    def __init__(self, i2c, address=DAPLINK_BRIDGE_DEFAULT_ADDR):
        self.i2c = i2c
        self.address = address
        self._buffer_1 = bytearray(1)

    # --------------------------------------------------
    # Low level I2C
    # --------------------------------------------------

    def _read_reg(self, reg, n=1):
        """Read n bytes from register."""
        if n == 1:
            self.i2c.readfrom_mem_into(self.address, reg, self._buffer_1)
            return self._buffer_1[0]
        return self.i2c.readfrom_mem(self.address, reg, n)

    def _write_reg(self, reg, data):
        """Write data bytes to register."""
        self.i2c.writeto_mem(self.address, reg, data)

    def _write_cmd(self, cmd):
        """Write a single command byte (no payload)."""
        self._buffer_1[0] = cmd
        self.i2c.writeto(self.address, self._buffer_1)

    def _writeto(self, data):
        """Write raw data frame to the bridge."""
        self.i2c.writeto(self.address, data)

    def _readfrom(self, n):
        """Read n raw bytes from the bridge."""
        return self.i2c.readfrom(self.address, n)

    # --------------------------------------------------
    # Device identification
    # --------------------------------------------------

    def device_id(self):
        """Read WHO_AM_I register. Expected: 0x4C."""
        return self._read_reg(CMD_WHO_AM_I)

    # --------------------------------------------------
    # Status and error registers
    # --------------------------------------------------

    def _status(self):
        """Read raw status register."""
        return self._read_reg(REG_STATUS)

    def _error(self):
        """Read raw error register."""
        return self._read_reg(REG_ERROR)

    def busy(self):
        """Return True if bridge is busy."""
        return bool(self._status() & STATUS_BUSY)

    def _wait_busy(self, timeout_ms=30000):
        """Poll busy bit until clear. Raises OSError on timeout."""
        elapsed = 0
        while self.busy():
            sleep_ms(5)
            elapsed += 5
            if elapsed >= timeout_ms:
                raise OSError("DAPLink bridge busy timeout")

    # --------------------------------------------------
    # Config zone (1 KB persistent storage in F103 internal flash)
    # --------------------------------------------------

    def clear_config(self):
        """Erase the 1 KB config zone."""
        self._wait_busy()
        self._write_cmd(CMD_CLEAR_CONFIG)
        sleep_ms(100)
        self._wait_busy()
        err = self._error()
        if err:
            raise OSError("DAPLink config clear error: 0x{:02X}".format(err))

    def write_config(self, data, offset=0):
        """Write data to the config zone at the given offset.

        Args:
            data: bytes or str to store.
            offset: byte offset within the config zone (0-1023).
        """
        if isinstance(data, str):
            data = data.encode()
        length = len(data)
        if offset < 0 or offset >= CONFIG_SIZE:
            raise ValueError("offset out of range: {}".format(offset))
        if offset + length > CONFIG_SIZE:
            raise ValueError("data exceeds config zone boundary")
        buf = bytearray(MAX_WRITE_CHUNK + 2)
        max_payload = len(buf) - 4
        buf[0] = CMD_WRITE_CONFIG
        pos = 0
        while pos < length:
            self._wait_busy()
            chunk_len = min(max_payload, length - pos)
            cur_offset = offset + pos
            buf[1] = (cur_offset >> 8) & 0xFF
            buf[2] = cur_offset & 0xFF
            buf[3] = chunk_len
            buf[4 : 4 + chunk_len] = data[pos : pos + chunk_len]
            for i in range(4 + chunk_len, len(buf)):
                buf[i] = 0
            self.i2c.writeto(self.address, buf)
            sleep_ms(50)
            pos += chunk_len
        self._wait_busy()
        err = self._error()
        if err:
            raise OSError("DAPLink config write error: 0x{:02X}".format(err))

    def read_config(self):
        """Read config zone content.

        Returns:
            bytes: config data up to first 0xFF, or b'' if empty.
        """
        result = bytearray()
        for page_offset in range(0, CONFIG_SIZE, SECTOR_SIZE):
            self._wait_busy()
            hi = (page_offset >> 8) & 0xFF
            lo = page_offset & 0xFF
            self._write_reg(CMD_READ_CONFIG, bytes([hi, lo]))
            sleep_ms(100)
            data = self.i2c.readfrom(self.address, SECTOR_SIZE)
            for i in range(SECTOR_SIZE):
                if data[i] == 0xFF:
                    return bytes(result)
                result.append(data[i])
        return bytes(result)
