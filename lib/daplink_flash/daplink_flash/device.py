from time import sleep_ms

from daplink_flash.const import *


class DaplinkFlash(object):
    """High-level flash file operations via the DAPLink bridge."""

    def __init__(self, bridge):
        self._bridge = bridge

    # --------------------------------------------------
    # Filename management
    # --------------------------------------------------

    def set_filename(self, name, ext):
        """Set 8.3 filename. name: max 8 chars, ext: max 3 chars."""
        self._bridge._wait_busy()
        n = name.upper().encode("ascii")[:FILENAME_LEN]
        e = ext.upper().encode("ascii")[:EXT_LEN]
        padded = n + b" " * (FILENAME_LEN - len(n)) + e + b" " * (EXT_LEN - len(e))
        self._bridge._write_reg(CMD_SET_FILENAME, padded)

    def get_filename(self):
        """Read current filename. Returns (name, ext) tuple, stripped."""
        self._bridge._wait_busy()
        raw = self._bridge._read_reg(CMD_GET_FILENAME, FILENAME_LEN + EXT_LEN)
        name = bytes(raw[:FILENAME_LEN]).decode().rstrip()
        ext = bytes(raw[FILENAME_LEN:]).decode().rstrip()
        return (name, ext)

    # --------------------------------------------------
    # Flash operations
    # --------------------------------------------------

    def clear_flash(self):
        """Erase entire flash memory."""
        self._bridge._wait_busy()
        self._bridge._write_cmd(CMD_CLEAR_FLASH)

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
            self._bridge._wait_busy()
            chunk_len = min(MAX_WRITE_CHUNK, length - offset)
            buf[1] = chunk_len
            buf[2 : 2 + chunk_len] = data[offset : offset + chunk_len]
            for i in range(2 + chunk_len, len(buf)):
                buf[i] = 0
            self._bridge._writeto(buf)
            offset += chunk_len
        self._bridge._wait_busy()
        err = self._bridge._error()
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
        self._bridge._wait_busy()
        self._bridge._write_reg(CMD_READ_SECTOR, bytes([sector >> 8, sector & 0xFF]))
        sleep_ms(200)
        return self._bridge._readfrom(SECTOR_SIZE)

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
