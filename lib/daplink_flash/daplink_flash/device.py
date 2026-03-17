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

    def _wait_busy(self, timeout_ms=30000):
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
        n = name.upper().encode("ascii")[:FILENAME_LEN]
        e = ext.upper().encode("ascii")[:EXT_LEN]
        padded = n + b" " * (FILENAME_LEN - len(n)) + e + b" " * (EXT_LEN - len(e))
        self._write_reg(CMD_SET_FILENAME, padded)

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
        self._wait_busy()
        err = self._error()
        if err:
            raise OSError("DAPLink Flash write error: 0x{:02X}".format(err))
        return length

    def write_line(self, text):
        """Append text + newline to current file."""
        return self.write(text + "\n")

    # --------------------------------------------------
    # Read operations
    # --------------------------------------------------

    def read_sector(self, sector):
        """Read a 256-byte sector from flash.

        Args:
            sector: sector number (0-32767).

        Returns:
            bytes: 256 bytes of data.
        """
        self._wait_busy()
        self._write_reg(CMD_READ_SECTOR, bytes([sector >> 8, sector & 0xFF]))
        # F103 processes the command in its 30ms hook, then sets up DMA.
        # After DMA setup, the F103 is no longer in listen mode — only
        # a plain readfrom() will work (no register-based status poll).
        sleep_ms(200)
        return self.i2c.readfrom(self.address, SECTOR_SIZE)

    def read(self, length=None):
        """Read file content from flash.

        Args:
            length: max bytes to read. If None, reads until first 0xFF.

        Returns:
            bytes: file content.
        """
        if length is not None and length <= 0:
            return b""
        result = bytearray()
        sector = 0
        while sector < MAX_SECTORS:
            data = self.read_sector(sector)
            for i in range(SECTOR_SIZE):
                if length is not None:
                    result.append(data[i])
                    if len(result) >= length:
                        return bytes(result)
                else:
                    if data[i] == 0xFF:
                        return bytes(result)
                    result.append(data[i])
            sector += 1
        return bytes(result)

    # --------------------------------------------------
    # Config zone (1 KB persistent storage in F103 internal flash)
    # --------------------------------------------------

    def clear_config(self):
        """Erase the 1 KB config zone."""
        self._wait_busy()
        self._write_cmd(CMD_CLEAR_CONFIG)
        sleep_ms(100)
        self._wait_busy()

    def write_config(self, data, offset=0):
        """Write data to the config zone at the given offset.

        The firmware performs a read-modify-write cycle so existing
        data outside the written range is preserved.

        Args:
            data: bytes or str to store.
            offset: byte offset within the config zone (0-1023).
        """
        if isinstance(data, str):
            data = data.encode()
        length = len(data)
        buf = bytearray(MAX_WRITE_CHUNK + 2)
        buf[0] = CMD_WRITE_CONFIG
        pos = 0
        while pos < length:
            self._wait_busy()
            chunk_len = min(MAX_WRITE_CHUNK - 3, length - pos)
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
