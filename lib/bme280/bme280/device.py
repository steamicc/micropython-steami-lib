import struct
from time import sleep_ms

from bme280.const import (
    BME280_CHIP_ID,
    BME280_I2C_DEFAULT_ADDR,
    CALIB_H_SIZE,
    CALIB_TP_SIZE,
    DATA_BLOCK_SIZE,
    FILTER_SHIFT,
    MODE_FORCED,
    MODE_MASK,
    MODE_NORMAL,
    MODE_SLEEP,
    OSRS_P_SHIFT,
    OSRS_T_SHIFT,
    OSRS_X1,
    REG_CALIB_HUM,
    REG_CALIB_TEMP_PRESS,
    REG_CHIP_ID,
    REG_CONFIG,
    REG_CTRL_HUM,
    REG_CTRL_MEAS,
    REG_DATA_START,
    REG_SOFT_RESET,
    REG_STATUS,
    RESET_DELAY_MS,
    SOFT_RESET_CMD,
    STANDBY_SHIFT,
    STATUS_IM_UPDATE,
    STATUS_MEASURING,
)
from bme280.exceptions import BME280InvalidDevice, BME280NotFound


class BME280(object):
    """MicroPython driver for the Bosch BME280 temperature, humidity, and pressure sensor."""

    def __init__(self, i2c, address=BME280_I2C_DEFAULT_ADDR):
        self.i2c = i2c
        self.address = address
        self.sea_level_pressure = 1013.25
        self._check_device()
        self._wait_boot()
        self._read_calibration()
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
    # Calibration data
    # --------------------------------------------------

    def _read_calibration(self):
        """Read factory calibration (trimming) parameters from NVM."""
        # Block 1: 0x88, 26 bytes — T1..T3, P1..P9, _, H1
        tp = self._read_block(REG_CALIB_TEMP_PRESS, CALIB_TP_SIZE)
        (
            self.dig_T1, self.dig_T2, self.dig_T3,
            self.dig_P1, self.dig_P2, self.dig_P3,
            self.dig_P4, self.dig_P5, self.dig_P6,
            self.dig_P7, self.dig_P8, self.dig_P9,
            _, self.dig_H1,
        ) = struct.unpack("<HhhHhhhhhhhhBB", tp)

        # Block 2: 0xE1, 7 bytes — H2..H6
        hum = self._read_block(REG_CALIB_HUM, CALIB_H_SIZE)
        self.dig_H2 = struct.unpack("<h", hum[0:2])[0]
        self.dig_H3 = hum[2]
        # H4 and H5 share register 0xE5 (12-bit values packed across 3 bytes)
        self.dig_H4 = (hum[3] << 4) | (hum[4] & 0x0F)
        if self.dig_H4 > 2047:
            self.dig_H4 -= 4096
        self.dig_H5 = (hum[4] >> 4) | (hum[5] << 4)
        if self.dig_H5 > 2047:
            self.dig_H5 -= 4096
        self.dig_H6 = struct.unpack("<b", bytes([hum[6]]))[0]

        # t_fine is computed during temperature compensation
        self.t_fine = 0

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
        """Apply default configuration."""
        # Set humidity oversampling (must be written before ctrl_meas)
        self._write_reg(REG_CTRL_HUM, OSRS_X1)
        # Set temperature and pressure oversampling, sleep mode
        self._write_reg(
            REG_CTRL_MEAS,
            (OSRS_X1 << OSRS_T_SHIFT) | (OSRS_X1 << OSRS_P_SHIFT) | MODE_SLEEP,
        )

    def _wait_boot(self, timeout_ms=50):
        """Wait for NVM data copy to complete. Raises on timeout."""
        for _ in range(timeout_ms // 5):
            if not (self._read_reg(REG_STATUS) & STATUS_IM_UPDATE):
                return
            sleep_ms(5)
        raise OSError("BME280 NVM copy timeout")

    def device_id(self):
        """Read chip ID register. Expected: 0x60."""
        return self._read_reg(REG_CHIP_ID)

    def soft_reset(self):
        """Perform a soft reset. Device returns to power-on defaults."""
        self._write_reg(REG_SOFT_RESET, SOFT_RESET_CMD)
        sleep_ms(RESET_DELAY_MS)
        self._wait_boot()

    def reset(self):
        """Reset, re-read calibration, and reconfigure."""
        self.soft_reset()
        self._read_calibration()
        self._configure_default()

    # --------------------------------------------------
    # Power and mode control
    # --------------------------------------------------

    def power_off(self):
        """Enter sleep mode. Stops all measurements."""
        ctrl = self._read_reg(REG_CTRL_MEAS)
        self._write_reg(REG_CTRL_MEAS, ctrl & ~MODE_MASK)

    def power_on(self):
        """Enter normal mode. Continuous measurements at configured standby rate."""
        ctrl = self._read_reg(REG_CTRL_MEAS)
        self._write_reg(REG_CTRL_MEAS, (ctrl & ~MODE_MASK) | MODE_NORMAL)

    def set_continuous(self, standby=None):
        """Start continuous measurements in normal mode.

        Args:
            standby: standby time constant (STANDBY_0_5_MS .. STANDBY_1000_MS).
                     If None, the current config register value is kept.
        """
        if standby is not None:
            self.set_standby(standby)
        self.power_on()

    # --------------------------------------------------
    # Sensor configuration
    # --------------------------------------------------

    def set_oversampling(self, temperature=None, pressure=None, humidity=None):
        """Configure oversampling for one or more channels.

        Args:
            temperature: OSRS_SKIP .. OSRS_X16 (None = keep current).
            pressure: OSRS_SKIP .. OSRS_X16 (None = keep current).
            humidity: OSRS_SKIP .. OSRS_X16 (None = keep current).
        """
        if humidity is not None:
            self._write_reg(REG_CTRL_HUM, humidity)
        ctrl = self._read_reg(REG_CTRL_MEAS)
        if temperature is not None:
            ctrl = (ctrl & ~(0x07 << OSRS_T_SHIFT)) | (temperature << OSRS_T_SHIFT)
        if pressure is not None:
            ctrl = (ctrl & ~(0x07 << OSRS_P_SHIFT)) | (pressure << OSRS_P_SHIFT)
        # ctrl_meas must always be rewritten: changes to ctrl_hum are only
        # latched when ctrl_meas is written (datasheet section 5.4.3).
        self._write_reg(REG_CTRL_MEAS, ctrl)

    def set_iir_filter(self, coefficient):
        """Configure the IIR filter coefficient.

        Args:
            coefficient: FILTER_OFF .. FILTER_16.
        """
        config = self._read_reg(REG_CONFIG)
        config = (config & ~(0x07 << FILTER_SHIFT)) | (coefficient << FILTER_SHIFT)
        self._write_reg(REG_CONFIG, config)

    def set_standby(self, standby):
        """Configure the standby time for normal mode.

        Args:
            standby: STANDBY_0_5_MS .. STANDBY_1000_MS.
        """
        config = self._read_reg(REG_CONFIG)
        config = (config & ~(0x07 << STANDBY_SHIFT)) | (standby << STANDBY_SHIFT)
        self._write_reg(REG_CONFIG, config)

    # --------------------------------------------------
    # Status
    # --------------------------------------------------

    def _status(self):
        """Return the raw STATUS register value."""
        return self._read_reg(REG_STATUS)

    def data_ready(self):
        """Return True when all measurements are available."""
        return not (self._status() & STATUS_MEASURING)

    def temperature_ready(self):
        """Return True when temperature data is available."""
        return self.data_ready()

    def pressure_ready(self):
        """Return True when pressure data is available."""
        return self.data_ready()

    def humidity_ready(self):
        """Return True when humidity data is available."""
        return self.data_ready()

    # --------------------------------------------------
    # Forced measurement trigger
    # --------------------------------------------------

    def _is_sleep_mode(self):
        """Return True if the sensor is in sleep mode."""
        return (self._read_reg(REG_CTRL_MEAS) & MODE_MASK) == MODE_SLEEP

    def _ensure_data(self):
        """Trigger a forced measurement if the sensor is in sleep mode.

        In normal mode this is a no-op. In sleep mode it triggers a
        single conversion and waits for completion so that subsequent
        register reads return fresh data.
        """
        if self._is_sleep_mode():
            self.trigger_one_shot()
            self._wait_measurement()

    def trigger_one_shot(self):
        """Trigger a single forced measurement. Poll data_ready() for completion."""
        ctrl = self._read_reg(REG_CTRL_MEAS)
        self._write_reg(REG_CTRL_MEAS, (ctrl & ~MODE_MASK) | MODE_FORCED)

    def _wait_measurement(self, timeout_ms=100):
        """Wait for measurement to complete. Raises on timeout."""
        for _ in range(timeout_ms // 5):
            if self.data_ready():
                return
            sleep_ms(5)
        raise OSError("BME280 measurement timeout")

    # --------------------------------------------------
    # Raw data burst read
    # --------------------------------------------------

    def _read_raw(self):
        """Read raw ADC values via burst read (0xF7-0xFE, 8 bytes).

        Returns (raw_temp, raw_press, raw_hum) as 20-bit/20-bit/16-bit integers.
        """
        data = self._read_block(REG_DATA_START, DATA_BLOCK_SIZE)
        raw_press = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        raw_temp = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
        raw_hum = (data[6] << 8) | data[7]
        return raw_temp, raw_press, raw_hum

    # --------------------------------------------------
    # Compensation formulas (BME280 datasheet section 4.2.3)
    # --------------------------------------------------

    def _compensate_temperature(self, raw_temp):
        """Compute compensated temperature in hundredths of °C. Updates t_fine."""
        var1 = (((raw_temp >> 3) - (self.dig_T1 << 1)) * self.dig_T2) >> 11
        var2 = (
            (((raw_temp >> 4) - self.dig_T1) * ((raw_temp >> 4) - self.dig_T1)) >> 12
        ) * self.dig_T3 >> 14
        self.t_fine = var1 + var2
        return (self.t_fine * 5 + 128) >> 8

    def _compensate_pressure(self, raw_press):
        """Compute compensated pressure in Pa (Q24.8 fixed point)."""
        var1 = self.t_fine - 128000
        var2 = var1 * var1 * self.dig_P6
        var2 = var2 + ((var1 * self.dig_P5) << 17)
        var2 = var2 + (self.dig_P4 << 35)
        var1 = ((var1 * var1 * self.dig_P3) >> 8) + ((var1 * self.dig_P2) << 12)
        var1 = ((1 << 47) + var1) * self.dig_P1 >> 33
        if var1 == 0:
            return 0
        p = 1048576 - raw_press
        p = (((p << 31) - var2) * 3125) // var1
        var1 = (self.dig_P9 * (p >> 13) * (p >> 13)) >> 25
        var2 = (self.dig_P8 * p) >> 19
        return ((p + var1 + var2) >> 8) + (self.dig_P7 << 4)

    def _compensate_humidity(self, raw_hum):
        """Compute compensated humidity in Q22.10 fixed point."""
        h = self.t_fine - 76800
        h = (
            (((raw_hum << 14) - (self.dig_H4 << 20) - (self.dig_H5 * h)) + 16384)
            >> 15
        ) * (
            (
                (
                    (((h * self.dig_H6) >> 10) * (((h * self.dig_H3) >> 11) + 32768))
                    >> 10
                )
                + 2097152
            )
            * self.dig_H2
            + 8192
        ) >> 14
        h = h - (((((h >> 15) * (h >> 15)) >> 7) * self.dig_H1) >> 4)
        h = max(h, 0)
        h = min(h, 419430400)
        return h >> 12

    # --------------------------------------------------
    # Public measurement methods
    # --------------------------------------------------

    def temperature(self):
        """Return compensated temperature in °C (float).

        If the sensor is in sleep mode, a forced measurement is triggered
        automatically before reading.
        """
        self._ensure_data()
        raw_temp, _, _ = self._read_raw()
        return self._compensate_temperature(raw_temp) / 100.0

    def pressure_hpa(self):
        """Return compensated pressure in hPa (float).

        If the sensor is in sleep mode, a forced measurement is triggered
        automatically before reading.
        """
        self._ensure_data()
        raw_temp, raw_press, _ = self._read_raw()
        self._compensate_temperature(raw_temp)
        return self._compensate_pressure(raw_press) / 25600.0

    def humidity(self):
        """Return compensated relative humidity in %RH (float).

        If the sensor is in sleep mode, a forced measurement is triggered
        automatically before reading.
        """
        self._ensure_data()
        raw_temp, _, raw_hum = self._read_raw()
        self._compensate_temperature(raw_temp)
        return self._compensate_humidity(raw_hum) / 1024.0

    def read(self):
        """Return (temperature_c, pressure_hpa, humidity_rh) tuple.

        If the sensor is in sleep mode, a forced measurement is triggered
        automatically before reading.
        """
        self._ensure_data()
        raw_temp, raw_press, raw_hum = self._read_raw()
        temp_c = self._compensate_temperature(raw_temp) / 100.0
        press_hpa = self._compensate_pressure(raw_press) / 25600.0
        hum_rh = self._compensate_humidity(raw_hum) / 1024.0
        return temp_c, press_hpa, hum_rh

    def read_one_shot(self):
        """Trigger a forced measurement, wait, and return (temp_c, press_hpa, hum_rh).

        Reads registers directly without calling _ensure_data() to avoid
        a double trigger (forced mode returns the sensor to sleep).
        """
        self.trigger_one_shot()
        self._wait_measurement()
        raw_temp, raw_press, raw_hum = self._read_raw()
        temp_c = self._compensate_temperature(raw_temp) / 100.0
        press_hpa = self._compensate_pressure(raw_press) / 25600.0
        hum_rh = self._compensate_humidity(raw_hum) / 1024.0
        return temp_c, press_hpa, hum_rh

    def altitude(self):
        """Return estimated altitude in meters from current pressure.

        Uses the ICAO barometric formula with ``sea_level_pressure`` as
        reference (default 1013.25 hPa, adjustable).
        """
        p = self.pressure_hpa()
        return 44330.0 * (1.0 - (p / self.sea_level_pressure) ** 0.1903)
