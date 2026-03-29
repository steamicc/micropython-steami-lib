from time import sleep_ms

from bme280.const import (
    BME280_CHIP_ID,
    BME280_I2C_DEFAULT_ADDR,
    MODE_SLEEP,
    OSRS_P_SHIFT,
    OSRS_T_SHIFT,
    OSRS_X1,
    REG_CHIP_ID,
    REG_CTRL_HUM,
    REG_CTRL_MEAS,
    REG_SOFT_RESET,
    REG_STATUS,
    RESET_DELAY_MS,
    SOFT_RESET_CMD,
    STATUS_IM_UPDATE,
)
from bme280.exceptions import BME280InvalidDevice, BME280NotFound


class BME280(object):
    """MicroPython driver for the Bosch BME280 temperature, humidity, and pressure sensor."""

    def __init__(self, i2c, address=BME280_I2C_DEFAULT_ADDR):
        self.i2c = i2c
        self.address = address
        self._check_device()
        self._configure_default()

    # --------------------------------------------------
    # Low level I2C
    # --------------------------------------------------

    def _read_reg(self, reg):
        """Read a single byte from register."""
        return self.i2c.readfrom_mem(self.address, reg, 1)[0]

    def _read_block(self, reg, length):
        """Read a block of bytes from consecutive registers."""
        return self.i2c.readfrom_mem(self.address, reg, length)

    def _write_reg(self, reg, value):
        """Write a single byte to register."""
        self.i2c.writeto_mem(self.address, reg, bytes([value]))

    # --------------------------------------------------
    # Device identification and initialization
    # --------------------------------------------------

    def _check_device(self):
        """Verify device presence and ID."""
        try:
            chip_id = self.device_id()
        except OSError as err:
            raise BME280NotFound(
                "BME280 not found at address 0x{:02X}".format(self.address)
            ) from err
        if chip_id != BME280_CHIP_ID:
            raise BME280InvalidDevice(
                "Expected chip ID 0x{:02X}, got 0x{:02X}".format(BME280_CHIP_ID, chip_id)
            )

    def _configure_default(self):
        """Apply default configuration after reset."""
        # Wait for NVM copy to complete
        self._wait_boot()
        # Set humidity oversampling (must be written before ctrl_meas)
        self._write_reg(REG_CTRL_HUM, OSRS_X1)
        # Set temperature and pressure oversampling, sleep mode
        self._write_reg(
            REG_CTRL_MEAS,
            (OSRS_X1 << OSRS_T_SHIFT) | (OSRS_X1 << OSRS_P_SHIFT) | MODE_SLEEP,
        )

    def _wait_boot(self, timeout_ms=50):
        """Wait for NVM data copy to complete."""
        for _ in range(timeout_ms // 5):
            if not (self._read_reg(REG_STATUS) & STATUS_IM_UPDATE):
                return
            sleep_ms(5)

    def device_id(self):
        """Read chip ID register. Expected: 0x60."""
        return self._read_reg(REG_CHIP_ID)

    def soft_reset(self):
        """Perform a soft reset. Device returns to power-on defaults."""
        self._write_reg(REG_SOFT_RESET, SOFT_RESET_CMD)
        sleep_ms(RESET_DELAY_MS)
        self._wait_boot()

    def reset(self):
        """Reset and reconfigure."""
        self.soft_reset()
        self._configure_default()
