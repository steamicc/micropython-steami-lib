from time import sleep_ms, ticks_ms, ticks_diff

from wsen_pads.const import *
from wsen_pads.exceptions import *


class WSEN_PADS(object):
    """
    MicroPython driver for the Würth Elektronik WSEN-PADS pressure sensor.

    This V1 driver supports:
    - I2C communication
    - device identification
    - pressure and temperature reading
    - one-shot acquisition
    - continuous mode configuration
    - low-noise and low-pass filter basic configuration
    - soft reset and reboot
    """

    def __init__(self, i2c, address=WSEN_PADS_I2C_DEFAULT_ADDR):
        """
        Create a WSEN-PADS device instance.

        Parameters:
            i2c: an initialized machine.I2C object
            address: 7-bit I2C address of the sensor
        """
        self.i2c = i2c
        self.address = address
        self._temp_gain = 1.0
        self._temp_offset = 0.0

        # Wait for the sensor boot sequence after power-up.
        sleep_ms(BOOT_DELAY_MS)

        # Check that the sensor is present on the I2C bus.
        if not self._is_present():
            raise WSENPADSDeviceNotFound(
                "WSEN-PADS not found at I2C address 0x{:02X}".format(self.address)
            )

        # Wait until the internal boot process is complete.
        self._wait_boot()

        # Verify that the detected sensor is really a WSEN-PADS.
        self._check_device()

        # Apply a safe default configuration.
        self._configure_default()

    # ---------------------------------------------------------------------
    # Low-level I2C helpers
    # ---------------------------------------------------------------------

    def _is_present(self):
        """Return True if the device address is visible on the I2C bus."""
        try:
            return self.address in self.i2c.scan()
        except Exception:
            return False

    def _read_reg(self, reg):
        """Read and return one unsigned byte from a register."""
        return self.i2c.readfrom_mem(self.address, reg, 1)[0]

    def _read_block(self, reg, length):
        """Read and return multiple bytes starting at a register."""
        return self.i2c.readfrom_mem(self.address, reg, length)

    def _write_reg(self, reg, value):
        """Write one unsigned byte to a register."""
        self.i2c.writeto_mem(self.address, reg, bytes((value & 0xFF,)))

    def _update_reg(self, reg, mask, value):
        """
        Update selected bits in a register.

        Only the bits set in 'mask' are modified. Other bits are preserved.
        """
        current = self._read_reg(reg)
        current = (current & ~mask) | (value & mask)
        self._write_reg(reg, current)

    # ---------------------------------------------------------------------
    # Internal conversion helpers
    # ---------------------------------------------------------------------

    @staticmethod
    def _to_signed24(value):
        """Convert a 24-bit integer to a signed Python integer."""
        if value & 0x800000:
            value -= 0x1000000
        return value

    @staticmethod
    def _to_signed16(value):
        """Convert a 16-bit integer to a signed Python integer."""
        if value & 0x8000:
            value -= 0x10000
        return value

    # ---------------------------------------------------------------------
    # Internal device helpers
    # ---------------------------------------------------------------------

    def _wait_boot(self, timeout_ms=20):
        """
        Wait until the BOOT_ON flag is cleared.

        The sensor sets BOOT_ON while internal trimming parameters are loaded.
        """
        start = ticks_ms()
        while self._read_reg(REG_INT_SOURCE) & INT_SOURCE_BOOT_ON:
            if ticks_diff(ticks_ms(), start) > timeout_ms:
                raise WSENPADSTimeout("WSEN-PADS boot timeout")
            sleep_ms(1)

    def _check_device(self):
        """Raise an exception if the device ID does not match."""
        device_id = self.device_id()
        if device_id != WSEN_PADS_DEVICE_ID:
            raise WSENPADSInvalidDevice(
                "Invalid WSEN-PADS device ID: 0x{:02X}".format(device_id)
            )

    def _configure_default(self):
        """
        Apply a safe default configuration.

        Default choices:
        - power-down mode
        - block data update enabled
        - register auto-increment enabled
        - low-noise disabled
        - low-pass filter disabled
        """
        self.power_down()

        # Enable automatic register address increment.
        self._update_reg(REG_CTRL_2, CTRL2_IF_ADD_INC, CTRL2_IF_ADD_INC)

        # Enable block data update to avoid partial register updates
        # during multi-byte reads.
        self._update_reg(REG_CTRL_1, CTRL1_BDU, CTRL1_BDU)

        # Make sure low-noise is disabled by default.
        self._update_reg(REG_CTRL_2, CTRL2_LOW_NOISE_EN, 0)

    # ---------------------------------------------------------------------
    # Identification and status
    # ---------------------------------------------------------------------

    def device_id(self):
        """Return the value of the DEVICE_ID register."""
        return self._read_reg(REG_DEVICE_ID)

    def status(self):
        """Return the raw STATUS register value."""
        return self._read_reg(REG_STATUS)

    def pressure_available(self):
        """Return True when new pressure data is available."""
        return bool(self.status() & STATUS_P_DA)

    def temperature_available(self):
        """Return True when new temperature data is available."""
        return bool(self.status() & STATUS_T_DA)

    def is_ready(self):
        """
        Return True when both pressure and temperature data are available.

        This is mainly useful in continuous mode.
        """
        status = self.status()
        return bool((status & STATUS_P_DA) and (status & STATUS_T_DA))

    # ---------------------------------------------------------------------
    # Power and reset control
    # ---------------------------------------------------------------------

    def power_down(self):
        """Put the device in power-down mode by setting ODR = 000."""
        self._update_reg(REG_CTRL_1, CTRL1_ODR_MASK, ODR_POWER_DOWN << CTRL1_ODR_SHIFT)

    def soft_reset(self):
        """
        Trigger a software reset.

        This restores user registers to their default values.
        """
        self._update_reg(REG_CTRL_2, CTRL2_SWRESET, CTRL2_SWRESET)
        sleep_ms(1)

        # Re-apply the minimal driver configuration after reset.
        self._configure_default()

    def reboot(self):
        """
        Trigger a reboot of the internal memory content.

        This reloads trimming parameters from internal non-volatile memory.
        """
        self._update_reg(REG_CTRL_2, CTRL2_BOOT, CTRL2_BOOT)
        self._wait_boot()

        # Re-apply the minimal driver configuration after reboot.
        self._configure_default()

    # ---------------------------------------------------------------------
    # Raw data reading
    # ---------------------------------------------------------------------

    def _is_power_down(self):
        """Return True if the sensor is in power-down mode (ODR = 000)."""
        return (self._read_reg(REG_CTRL_1) & CTRL1_ODR_MASK) == 0

    def _ensure_data(self):
        """Trigger a one-shot conversion if the sensor is in power-down mode."""
        if self._is_power_down():
            self.trigger_one_shot()
            for _ in range(50):
                if self._read_reg(REG_STATUS) & STATUS_P_DA:
                    return
                sleep_ms(2)
            raise OSError("WSEN-PADS data ready timeout")

    def pressure_raw(self):
        """
        Read and return raw pressure as a signed 24-bit integer.

        If the sensor is in power-down mode, a one-shot conversion is
        triggered automatically before reading.
        """
        self._ensure_data()
        data = self._read_block(REG_DATA_P_XL, 3)
        raw = (data[2] << 16) | (data[1] << 8) | data[0]
        return self._to_signed24(raw)

    def temperature_raw(self):
        """
        Read and return raw temperature as a signed 16-bit integer.

        If the sensor is in power-down mode, a one-shot conversion is
        triggered automatically before reading.
        """
        self._ensure_data()
        data = self._read_block(REG_DATA_T_L, 2)
        raw = (data[1] << 8) | data[0]
        return self._to_signed16(raw)

    # ---------------------------------------------------------------------
    # Converted data reading
    # ---------------------------------------------------------------------

    def pressure(self):
        """
        Read and return pressure in hPa.
        """
        return self.pressure_raw() * PRESSURE_HPA_PER_DIGIT

    def pressure_pa(self):
        """
        Read and return pressure in Pa.
        """
        return self.pressure_raw() * PRESSURE_PA_PER_DIGIT

    def pressure_kpa(self):
        """
        Read and return pressure in kPa.
        """
        return self.pressure_raw() * PRESSURE_KPA_PER_DIGIT

    def temperature(self):
        """
        Read and return temperature in degrees Celsius.
        """
        factory = self.temperature_raw() * TEMPERATURE_C_PER_DIGIT
        return self._temp_gain * factory + self._temp_offset

    def read(self):
        """
        Read and return both pressure and temperature.

        A one-shot conversion is triggered to ensure fresh data.

        Returns:
            tuple: (pressure_hpa, temperature_c)
        """
        self.trigger_one_shot()
        p_data = self._read_block(REG_DATA_P_XL, 3)
        p_raw = self._to_signed24((p_data[2] << 16) | (p_data[1] << 8) | p_data[0])
        t_data = self._read_block(REG_DATA_T_L, 2)
        t_raw = self._to_signed16((t_data[1] << 8) | t_data[0])
        t_c = self._temp_gain * (t_raw * TEMPERATURE_C_PER_DIGIT) + self._temp_offset
        return p_raw * PRESSURE_HPA_PER_DIGIT, t_c

    # ---------------------------------------------------------------------
    # One-shot mode
    # ---------------------------------------------------------------------

    def trigger_one_shot(self, low_noise=False):
        """
        Trigger a single conversion.

        The device must be in power-down mode before setting ONE_SHOT.
        The function blocks until the typical conversion time has elapsed.

        Parameters:
            low_noise: False for low-power mode, True for low-noise mode
        """
        self.power_down()

        # LOW_NOISE_EN must only be changed while in power-down mode.
        if low_noise:
            self._update_reg(REG_CTRL_2, CTRL2_LOW_NOISE_EN, CTRL2_LOW_NOISE_EN)
        else:
            self._update_reg(REG_CTRL_2, CTRL2_LOW_NOISE_EN, 0)

        # Start one-shot conversion.
        self._update_reg(REG_CTRL_2, CTRL2_ONE_SHOT, CTRL2_ONE_SHOT)

        # Wait for typical conversion completion time.
        if low_noise:
            sleep_ms(ONE_SHOT_LOW_NOISE_DELAY_MS)
        else:
            sleep_ms(ONE_SHOT_LOW_POWER_DELAY_MS)

    def read_one_shot(self, low_noise=False):
        """
        Trigger one conversion and return converted pressure and temperature.

        Returns:
            tuple: (pressure_hpa, temperature_c)
        """
        return self.read()

    # ---------------------------------------------------------------------
    # Continuous mode
    # ---------------------------------------------------------------------

    def set_continuous(
        self,
        odr=ODR_1_HZ,
        low_noise=False,
        low_pass=False,
        low_pass_strong=False,
    ):
        """
        Configure continuous measurement mode.

        Parameters:
            odr: one of the ODR_* constants
            low_noise: enable low-noise mode
            low_pass: enable LPF2 on pressure output
            low_pass_strong: when LPF2 is enabled:
                             False -> bandwidth ODR/9
                             True  -> bandwidth ODR/20
        """
        if odr not in (
            ODR_1_HZ,
            ODR_10_HZ,
            ODR_25_HZ,
            ODR_50_HZ,
            ODR_75_HZ,
            ODR_100_HZ,
            ODR_200_HZ,
        ):
            raise ValueError("Invalid ODR value")

        # Low-noise mode is not allowed at 100 Hz and 200 Hz.
        if low_noise and odr in (ODR_100_HZ, ODR_200_HZ):
            raise ValueError("Low-noise mode is not available at 100 Hz or 200 Hz")

        # Enter power-down before changing LOW_NOISE_EN as required by the sensor.
        self.power_down()

        # Configure low-noise mode and auto-increment.
        ctrl2_value = CTRL2_IF_ADD_INC
        if low_noise:
            ctrl2_value |= CTRL2_LOW_NOISE_EN
        self._update_reg(
            REG_CTRL_2,
            CTRL2_IF_ADD_INC | CTRL2_LOW_NOISE_EN,
            ctrl2_value,
        )

        # Build CTRL_1 configuration.
        ctrl1_value = CTRL1_BDU | (odr << CTRL1_ODR_SHIFT)

        if low_pass:
            ctrl1_value |= CTRL1_EN_LPFP
            if low_pass_strong:
                ctrl1_value |= CTRL1_LPFP_CFG

        self._write_reg(REG_CTRL_1, ctrl1_value)

    # ---------------------------------------------------------------------
    # Optional helper methods
    # ---------------------------------------------------------------------

    def enable_low_pass(self, strong=False):
        """
        Enable the optional LPF2 pressure filter.

        This helper preserves the current ODR and only updates filter bits.
        """
        current = self._read_reg(REG_CTRL_1)
        current |= CTRL1_EN_LPFP
        if strong:
            current |= CTRL1_LPFP_CFG
        else:
            current &= ~CTRL1_LPFP_CFG
        self._write_reg(REG_CTRL_1, current)

    def disable_low_pass(self):
        """Disable the optional LPF2 pressure filter."""
        current = self._read_reg(REG_CTRL_1)
        current &= ~(CTRL1_EN_LPFP | CTRL1_LPFP_CFG)
        self._write_reg(REG_CTRL_1, current)

    # ---------------------------------------------------------------------
    # Temperature calibration
    # ---------------------------------------------------------------------

    def set_temp_offset(self, offset_c):
        """Set a temperature offset in °C (gain remains 1.0).

        Args:
            offset_c: offset value in degrees Celsius.
        """
        self._temp_gain = 1.0
        self._temp_offset = float(offset_c)

    def calibrate_temperature(self, ref_low, measured_low, ref_high, measured_high):
        """Two-point calibration from reference measurements.

        Computes gain and offset so that the sensor reading is adjusted
        to match reference values at two temperature points.

        Args:
            ref_low: reference temperature at the low point (°C).
            measured_low: sensor reading at the low point (°C).
            ref_high: reference temperature at the high point (°C).
            measured_high: sensor reading at the high point (°C).
        """
        delta = float(measured_high - measured_low)
        if delta == 0.0:
            raise ValueError("measured_low and measured_high must differ")
        self._temp_gain = float(ref_high - ref_low) / delta
        self._temp_offset = float(ref_low) - self._temp_gain * float(measured_low)
