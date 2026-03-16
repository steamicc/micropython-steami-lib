from time import sleep_ms

from daplink_flash.const import *


class DaplinkFlash(object):
    """MicroPython driver for the DAPLink Flash bridge (STM32F103 → W25Q64JV)."""

    def __init__(self, i2c, address=DAPLINK_FLASH_DEFAULT_ADDR):
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
        """Return True if flash is busy."""
        return bool(self._status() & STATUS_BUSY)

    def _wait_busy(self, timeout_ms=1000):
        """Poll busy bit until clear. Raises OSError on timeout."""
        elapsed = 0
        while self.busy():
            sleep_ms(5)
            elapsed += 5
            if elapsed >= timeout_ms:
                raise OSError("DAPLink Flash busy timeout")

    # --------------------------------------------------
    # Filename management
    # --------------------------------------------------

    def set_filename(self, name, ext):
        """Set 8.3 filename. name: max 8 chars, ext: max 3 chars."""
        self._wait_busy()
        n = name.upper()[:FILENAME_LEN]
        e = ext.upper()[:EXT_LEN]
        padded = n + " " * (FILENAME_LEN - len(n)) + e + " " * (EXT_LEN - len(e))
        self._write_reg(CMD_SET_FILENAME, padded.encode())

    def get_filename(self):
        """Read current filename. Returns (name, ext) tuple, stripped."""
        self._wait_busy()
        raw = self._read_reg(CMD_GET_FILENAME, FILENAME_LEN + EXT_LEN)
        name = bytes(raw[:FILENAME_LEN]).decode().rstrip()
        ext = bytes(raw[FILENAME_LEN:]).decode().rstrip()
        return (name, ext)

    # --------------------------------------------------
    # Flash operations
    # --------------------------------------------------

    def clear_flash(self):
        """Erase entire flash memory."""
        self._wait_busy()
        self._write_cmd(CMD_CLEAR_FLASH)

    def write(self, data):
        """Append data to current file. data: bytes or str.

        Returns the number of bytes written.
        """
        if isinstance(data, str):
            data = data.encode()
        offset = 0
        length = len(data)
        buf = bytearray(MAX_WRITE_CHUNK + 2)
        buf[0] = CMD_WRITE_DATA
        while offset < length:
            self._wait_busy()
            chunk_len = min(MAX_WRITE_CHUNK, length - offset)
            buf[1] = chunk_len
            buf[2 : 2 + chunk_len] = data[offset : offset + chunk_len]
            # Zero-pad remainder
            for i in range(2 + chunk_len, len(buf)):
                buf[i] = 0
            self.i2c.writeto(self.address, buf)
            offset += chunk_len
        return length

    def write_line(self, text):
        """Append text + newline to current file."""
        return self.write(text + "\n")
