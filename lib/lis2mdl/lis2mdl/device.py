# device.py
# This driver is for the LIS2MDL magnetometer sensor. It provides methods for initialization, calibration, and reading magnetic field data.

from machine import I2C
from lis2mdl.const import *
from time import sleep_ms
import math


class LIS2MDL(object):
    # Default calibration offsets and scales for the magnetometer
    x_off = 0
    y_off = 0
    z_off = 0

    x_scale = 1
    y_scale = 1
    z_scale = 1

    def __init__(
        self,
        i2c,
        address=LIS2MDL_I2C_ADDR,
        odr_hz=10,
        temp_comp=True,
        low_power=False,
        drdy_enable=False,
    ):
        # Initialize the LIS2MDL sensor with the given I2C interface and settings.
        self.i2c = i2c
        self.address = address
        self.writebuffer = bytearray(1)
        self.readbuffer = bytearray(1)

        self._temp_gain = 1.0
        self._temp_offset = 0.0
        self._temp_base_offset = LIS2MDL_TEMP_OFFSET

        # Perform a soft reset to ensure the sensor starts in a known state.
        self._write_reg(LIS2MDL_CFG_REG_A, 0x20)  # SOFT_RST=1 (not 0x10)
        try:
            sleep_ms(10)  # Small delay for reset to complete
        except Exception:
            pass

        # Configure the sensor's operating mode, output data rate, and other settings.
        odr_bits = {10: 0b00, 20: 0b01, 50: 0b10, 100: 0b11}.get(odr_hz, 0b00)
        comp = 1 if temp_comp else 0
        lp = 1 if low_power else 0
        cfg_a = (comp << 7) | (lp << 4) | (odr_bits << 2) | 0b00
        self._write_reg(LIS2MDL_CFG_REG_A, cfg_a)  # Essential to exit IDLE mode

        # Configure low-pass filter and other optional settings.
        self._write_reg(LIS2MDL_CFG_REG_B, 0x00)  # Default: LPF and offset cancellation off

        # Enable block data update and optionally configure the DRDY pin.
        cfg_c = 0x10 | (0x01 if drdy_enable else 0x00)
        self._write_reg(LIS2MDL_CFG_REG_C, cfg_c)

    ##
    # --- SET functions ---
    ##

    # --- Modes / frequency (CFG_REG_A: 0x60) ---
    def set_mode(self, mode: str):
        # MD1..MD0: 00=continuous, 01=single, 11=idle
        md = {"continuous": 0b00, "single": 0b01, "idle": 0b11}.get(mode, 0b00)
        reg = self._read_reg(LIS2MDL_CFG_REG_A)
        reg = (reg & ~0b11) | md
        self._write_reg(LIS2MDL_CFG_REG_A, reg)

    def set_odr(self, hz: int):
        # ODR1..0: 00=10Hz, 01=20Hz, 10=50Hz, 11=100Hz
        odr_bits = {10: 0b00, 20: 0b01, 50: 0b10, 100: 0b11}.get(hz, 0b00)
        reg = self._read_reg(LIS2MDL_CFG_REG_A)
        reg = (reg & ~(0b11 << 2)) | (odr_bits << 2)
        self._write_reg(LIS2MDL_CFG_REG_A, reg)

    def set_low_power(self, enabled: bool):
        # LP bit (bit4) : 0=High-Res, 1=Low-Power
        reg = self._read_reg(LIS2MDL_CFG_REG_A)
        if enabled:
            reg |= 1 << 4
        else:
            reg &= ~(1 << 4)
        self._write_reg(LIS2MDL_CFG_REG_A, reg)

    # --- Filters / offset cancellation (CFG_REG_B: 0x61) ---
    def set_low_pass(self, enabled: bool):
        # LPF (bit0)
        reg = self._read_reg(LIS2MDL_CFG_REG_B)
        if enabled:
            reg |= 1 << 0
        else:
            reg &= ~(1 << 0)
        self._write_reg(LIS2MDL_CFG_REG_B, reg)

    def set_offset_cancellation(self, enabled: bool, oneshot: bool = False):
        # OFF_CANC (bit1), OFF_CANC_ONE_SHOT (bit4)
        reg = self._read_reg(LIS2MDL_CFG_REG_B)
        if enabled:
            reg |= 1 << 1
        else:
            reg &= ~(1 << 1)
        if oneshot:
            reg |= 1 << 4
        else:
            reg &= ~(1 << 4)
        self._write_reg(LIS2MDL_CFG_REG_B, reg)

    # --- Interface options / BDU (CFG_REG_C: 0x62) ---
    def set_bdu(self, enable=True):
        # BDU (bit4)
        reg = self._read_reg(LIS2MDL_CFG_REG_C)
        if enable:
            reg |= 1 << 4
        else:
            reg &= ~(1 << 4)
        self._write_reg(LIS2MDL_CFG_REG_C, reg)

    def set_endianness(self, big_endian: bool):
        # BLE (bit3)
        reg = self._read_reg(LIS2MDL_CFG_REG_C)
        if big_endian:
            reg |= 1 << 3
        else:
            reg &= ~(1 << 3)
        self._write_reg(LIS2MDL_CFG_REG_C, reg)

    def use_spi_4wire(self, enable: bool):
        # 4WSPI (bit2)
        reg = self._read_reg(LIS2MDL_CFG_REG_C)
        if enable:
            reg |= 1 << 2
        else:
            reg &= ~(1 << 2)
        self._write_reg(LIS2MDL_CFG_REG_C, reg)

    # --- Compass: heading offset & declination (software) ---
    _heading_offset_deg = 0.0  # user setting: align your physical 0°
    _declination_deg = 0.0  # true north vs magnetic north

    def set_heading_offset(self, deg: float):
        self._heading_offset_deg = float(deg)

    def set_declination(self, deg: float):
        self._declination_deg = float(deg)

    # (remember to correct your heading_flat_only with atan2(y, x) then + offsets)

    def _write_reg(self, reg, data):
        # Write a byte to a specific register.
        self.writebuffer[0] = data
        self.i2c.writeto_mem(self.address, reg, self.writebuffer)

    def _write_16(self, reg_l, value):
        value &= 0xFFFF
        self._write_reg(reg_l, value & 0xFF)
        self._write_reg(reg_l + 1, (value >> 8) & 0xFF)

    def set_hw_offsets(self, x: int, y: int, z: int):
        # writes to OFFSET_X/Y/Z_REG_L/H
        self._write_16(LIS2MDL_OFFSET_X_REG_L, x)
        self._write_16(LIS2MDL_OFFSET_Y_REG_L, y)
        self._write_16(LIS2MDL_OFFSET_Z_REG_L, z)

    ##
    # --- READ functions ---
    ##

    def _ensure_data(self):
        """Trigger a single conversion if the sensor is in idle mode."""
        if self.is_idle():
            self.set_mode("single")
            for _ in range(50):
                if self.data_ready():
                    return
                sleep_ms(2)
            raise OSError("LIS2MDL data ready timeout")

    def read_magnet_raw(self):
        """Reads the raw magnetic field (LSB). Same as read_magnet(), but more explicit."""
        return self.read_magnet()  # (x,y,z) int16 LSB

    def read_status(self) -> int:
        """Reads STATUS_REG (0x67)."""
        return self._read_reg(LIS2MDL_STATUS_REG)

    def data_ready(self) -> bool:
        """True if a new XYZ triplet is ready (Zyxda bit)."""
        return bool(self.read_status() & (1 << 3))

    def read_int_source(self) -> int:
        """Reads INT_SOURCE_REG (0x64): source of the interrupt."""
        return self._read_reg(LIS2MDL_INT_SOURCE_REG)

    def _read_reg(self, reg):
        # Read a byte from a specific register.
        self.i2c.readfrom_mem_into(self.address, reg, self.readbuffer)
        return self.readbuffer[0]

    # --- UNITS, CALIBRATION, MAGNITUDE ---

    _MAG_LSB_TO_uT = 0.15  # 1.5 mG/LSB ≈ 0.15 µT/LSB

    def read_magnet_uT(self):  # noqa: N802
        """Reads the magnetic field in µT, uncalibrated (simple conversion from LSB)."""
        x, y, z = self.read_magnet()
        return (
            x * self._MAG_LSB_TO_uT,
            y * self._MAG_LSB_TO_uT,
            z * self._MAG_LSB_TO_uT,
        )

    def read_magnet_calibrated_norm(self):
        """Reads the calibrated field (offset/scale per axis), normalized (unitless, ~circle in XY)."""
        x, y, z = self.read_magnet()
        x = (x - self.x_off) / self.x_scale
        y = (y - self.y_off) / self.y_scale
        z = (z - self.z_off) / self.z_scale
        return (x, y, z)

    def magnitude_uT(self) -> float:  # noqa: N802
        """Total magnetic field strength (µT)."""
        x, y, z = self.read_magnet_uT()
        return math.sqrt(x * x + y * y + z * z)

    @staticmethod
    def _to_int16(v):
        # Convert an unsigned 16-bit value to a signed 16-bit value.
        return v - 0x10000 if v & 0x8000 else v

    def read_magnet(self):
        # Read the raw magnetic field data (X, Y, Z) from the sensor.
        self._ensure_data()
        buf = self.i2c.readfrom_mem(self.address, LIS2MDL_OUTX_L_REG | 0x80, 6)
        x = self._to_int16((buf[1] << 8) | buf[0])
        y = self._to_int16((buf[3] << 8) | buf[2])
        z = self._to_int16((buf[5] << 8) | buf[4])
        return (x, y, z)

    # --- TEMPERATURE ---

    def read_temperature_raw(self) -> int:
        """Reads the raw temperature (LSB), 8 LSB/°C, absolute offset not guaranteed."""
        self._ensure_data()
        lo = self._read_reg(LIS2MDL_TEMP_OUT_L_REG)
        hi = self._read_reg(LIS2MDL_TEMP_OUT_H_REG)
        v = (hi << 8) | lo
        return v - 0x10000 if (v & 0x8000) else v

    def read_temperature_c(self) -> float:
        """Temperature in °C (8 LSB/°C + empirical offset).

        The LIS2MDL temperature sensor has no guaranteed absolute zero
        point (see datasheet Table 4).  The offset defaults to 25 °C
        based on empirical observation (confirmed by Zephyr RTOS
        PR #35912).  Use ``set_temp_offset()`` or ``calibrate_temperature()``
        to calibrate against a reference thermometer.
        """
        factory = self._temp_base_offset + self.read_temperature_raw() / LIS2MDL_TEMP_SENSITIVITY
        return self._temp_gain * factory + self._temp_offset

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

    # --- IDENTITY & HARDWARE OFFSETS ---

    def read_who_am_i(self) -> int:
        """Reads WHO_AM_I (should be 0x40)."""
        return self._read_reg(LIS2MDL_WHO_AM_I)

    def _read_16(self, reg_l) -> int:
        """Reads a signed 16-bit value from a _L (LSB) register."""
        lo = self._read_reg(reg_l)
        hi = self._read_reg(reg_l + 1)
        v = (hi << 8) | lo
        return v - 0x10000 if (v & 0x8000) else v

    def read_hw_offsets(self):
        """Reads the hardware offsets (OFFSET_* registers)."""
        ox = self._read_16(LIS2MDL_OFFSET_X_REG_L)
        oy = self._read_16(LIS2MDL_OFFSET_Y_REG_L)
        oz = self._read_16(LIS2MDL_OFFSET_Z_REG_L)
        return (ox, oy, oz)

    def read_calibration(self):
        # Return the current calibration offsets and scales.
        return (
            self.x_off,
            self.y_off,
            self.z_off,
            self.x_scale,
            self.y_scale,
            self.z_scale,
        )

    # --- DIAGNOSTIC / DUMP ---

    def read_registers(self, start_addr: int, length: int) -> bytes:
        """Dump of consecutive registers (useful for debugging)."""
        return self.i2c.readfrom_mem(self.address, start_addr, length)

    def read_all(self) -> dict:
        """Grouped reading useful for debug & logs."""
        raw = self.read_magnet_raw()
        mag_ut = self.read_magnet_uT()
        cal = self.read_magnet_calibrated_norm()
        temp = self.read_temperature_c()
        st = self.read_status()
        return {"raw": raw, "uT": mag_ut, "cal_norm": cal, "tempC": temp, "status": st}

    ##
    #  --- CALIBRATIONS ---
    ##

    def set_calibrate_step(self, xoff, yoff, zoff, xscale, yscale, zscale):
        # Set the calibration offsets and scales manually.
        self.x_off = xoff
        self.y_off = yoff
        self.z_off = zoff
        self.x_scale = xscale
        self.y_scale = yscale
        self.z_scale = zscale

    def calibrate_minmax_2d(self, samples=300, delay_ms=20):
        """
        MIN/MAX calibration while flat (XY only).
        Slowly rotate the board FLAT during acquisition.
        Updates x_off, y_off, x_scale, y_scale (leaves Z unchanged).
        """
        xmin = ymin = 1e9
        xmax = ymax = -1e9

        for _ in range(samples):
            x, y, _ = self.read_magnet()
            xmin = min(xmin, x)
            xmax = max(xmax, x)
            ymin = min(ymin, y)
            ymax = max(ymax, y)
            sleep_ms(delay_ms)

        self.x_off = (xmax + xmin) / 2.0
        self.y_off = (ymax + ymin) / 2.0
        self.x_scale = (xmax - xmin) / 2.0 or 1.0
        self.y_scale = (ymax - ymin) / 2.0 or 1.0
        # Option: normalize XY to the same average radius for a better 2D compass
        avg = (self.x_scale + self.y_scale) / 2.0
        self.x_scale = avg if self.x_scale != 0 else 1.0
        self.y_scale = avg if self.y_scale != 0 else 1.0

    def calibrate_minmax_3d(self, samples=600, delay_ms=20):
        """
        MIN/MAX calibration on 3 axes (rotate the board in ALL directions).
        Updates offsets + scales for X, Y, Z.
        """
        xmin = ymin = zmin = 1e9
        xmax = ymax = zmax = -1e9

        for _ in range(samples):
            x, y, z = self.read_magnet()
            xmin = min(xmin, x)
            xmax = max(xmax, x)
            ymin = min(ymin, y)
            ymax = max(ymax, y)
            zmin = min(zmin, z)
            zmax = max(zmax, z)
            sleep_ms(delay_ms)

        self.x_off = (xmax + xmin) / 2.0
        self.y_off = (ymax + ymin) / 2.0
        self.z_off = (zmax + zmin) / 2.0

        self.x_scale = (xmax - xmin) / 2.0 or 1.0
        self.y_scale = (ymax - ymin) / 2.0 or 1.0
        self.z_scale = (zmax - zmin) / 2.0 or 1.0

    def calibrate_apply(self, x, y, z):
        """
        Applies the current calibration (offset + scale per axis).
        Returns normalized ~unitless values.
        """
        xc = (x - self.x_off) / (self.x_scale or 1.0)
        yc = (y - self.y_off) / (self.y_scale or 1.0)
        zc = (z - self.z_off) / (self.z_scale or 1.0)
        return xc, yc, zc

    def calibrate_quality(self, samples_check=200, delay_ms=10):
        """
        Evaluates the quality of the current calibration over a short sample.
        Returns a dict with useful metrics: center (mean), anisotropy, XY radius dispersion.
        (Move the board a bit while flat during the measurement.)
        """
        xs = []
        ys = []
        zs = []
        for _ in range(samples_check):
            x, y, z = self.read_magnet()
            xc, yc, zc = self.calibrate_apply(x, y, z)
            xs.append(xc)
            ys.append(yc)
            zs.append(zc)
            sleep_ms(delay_ms)

        # Means (residual center)
        mx = sum(xs) / len(xs)
        my = sum(ys) / len(ys)
        mz = sum(zs) / len(zs)

        # Radius dispersion in the XY plane

        radii = [math.sqrt(x * x + y * y) for x, y in zip(xs, ys)]
        r_mean = sum(radii) / len(radii)
        r_var = sum((r - r_mean) ** 2 for r in radii) / len(radii)
        r_std = math.sqrt(r_var)

        # Simple anisotropy via standard deviations per axis
        def _std(arr, mean):
            v = sum((a - mean) ** 2 for a in arr) / len(arr)
            return math.sqrt(v)

        sx = _std(xs, mx)
        sy = _std(ys, my)
        sz = _std(zs, mz)
        aniso_xy = max(sx, sy) / (min(sx, sy) + 1e-9)

        return {
            "mean_xy": (mx, my),
            "mean_z": mz,
            "std_xy": (sx, sy),
            "std_z": sz,
            "r_mean_xy": r_mean,
            "r_std_xy": r_std,
            "anisotropy_xy": aniso_xy,  # ideal ≈ 1.0
        }

    def calibrate_reset(self):
        """Resets to a 'neutral' calibration (useful before re-calibrating)."""
        self.x_off = self.y_off = self.z_off = 0.0
        self.x_scale = self.y_scale = self.z_scale = 1.0

    def calibrate_step(self):
        # Simple alias to calibrate_minmax_3d
        return self.calibrate_minmax_3d()

    ##
    # --- Heading functions ---
    ##

    # angle filter via vector averaging (robust around 0/360)
    _hf_alpha = 0.0
    _hf_cos = None
    _hf_sin = None

    def set_heading_filter(self, alpha: float):
        """
        alpha=0 -> no filtering. 0.1..0.3 = light/medium smoothing.
        Filter by averaging cos/sin to avoid artifacts at 0/360°.
        """
        self._hf_alpha = max(0.0, min(1.0, alpha))
        self._hf_cos = None
        self._hf_sin = None

    @staticmethod
    def _normalize_deg(a):
        a = a % 360.0
        return a if a >= 0 else a + 360.0

    def _apply_heading_offsets(self, angle_deg):
        angle_deg = angle_deg + self._heading_offset_deg + self._declination_deg
        return self._normalize_deg(angle_deg)

    def _filter_heading(self, angle_deg):
        """Filters the angle via vector averaging; returns filtered angle (or raw if alpha=0)."""
        if self._hf_alpha <= 0.0:
            return angle_deg

        c = math.cos(math.radians(angle_deg))
        s = math.sin(math.radians(angle_deg))
        if self._hf_cos is None or self._hf_sin is None:
            self._hf_cos, self._hf_sin = c, s
        else:
            a = self._hf_alpha
            self._hf_cos = (1.0 - a) * self._hf_cos + a * c
            self._hf_sin = (1.0 - a) * self._hf_sin + a * s
            # light normalization to avoid amplitude drift
            norm_threshold = 1e-6
            norm = math.sqrt(self._hf_cos * self._hf_cos + self._hf_sin * self._hf_sin)
            if norm > norm_threshold:
                self._hf_cos /= norm
                self._hf_sin /= norm
        ang = math.degrees(math.atan2(self._hf_sin, self._hf_cos))
        return self._normalize_deg(ang)

    def heading_from_vectors(self, x, y, z, calibrated=True):
        """
        Computes the angle (0..360°) from a triplet.
        - calibrated=True: applies offset/scale per axis (recommended)
        - flat only (uses XY)
        """

        if calibrated:
            x = (x - self.x_off) / (self.x_scale or 1.0)
            y = (y - self.y_off) / (self.y_scale or 1.0)
        # IMPORTANT: atan2(Y, X)
        ang = math.degrees(math.atan2(x, y)) # atan2(Y, X) for compass heading (Y is forward, X is right)
        ang = self._apply_heading_offsets(ang)
        return self._filter_heading(ang)

    def heading_flat_only(self):
        """
        Reads the sensor and returns the angle (0..360°) assuming the board is FLAT.
        Uses XY (no tilt compensation).
        """
        x, y, z = self.read_magnet()
        return self.heading_from_vectors(x, y, z, calibrated=True)

    def heading_with_tilt_compensation(self, read_accel):
        """
        Tilt-compensated compass (if an accelerometer is available).
        read_accel() must return (ax, ay, az) ~g.
        """

        x, y, z = self.read_magnet()
        # 3D calibration
        x = (x - self.x_off) / (self.x_scale or 1.0)
        y = (y - self.y_off) / (self.y_scale or 1.0)
        z = (z - self.z_off) / (self.z_scale or 1.0)

        ax, ay, az = read_accel()
        # roll / pitch from accelerometer
        roll = math.atan2(ay, az)
        pitch = math.atan2(-ax, math.sqrt(ay * ay + az * az))
        # straighten the magnetic vector
        xh = x * math.cos(pitch) + z * math.sin(pitch)
        yh = (
            x * math.sin(roll) * math.sin(pitch)
            + y * math.cos(roll)
            - z * math.sin(roll) * math.cos(pitch)
        )
        ang = math.degrees(math.atan2(yh, xh))
        ang = self._apply_heading_offsets(ang)
        return self._filter_heading(ang)

    def direction_label(self, angle=None):
        """Returns N/NE/E/... ; if angle=None, reads heading_flat_only()."""
        if angle is None:
            angle = self.heading_flat_only()
        dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"]
        idx = int((angle) // 45)
        return dirs[idx]

    ##
    # --- Power/reset functions ---
    ##

    def get_mode(self) -> str:
        """Returns the current mode from MD1..0 (CFG_REG_A)."""
        r = self._read_reg(LIS2MDL_CFG_REG_A)
        md = r & 0b11
        return {0b00: "continuous", 0b01: "single", 0b11: "idle"}.get(md, "idle")

    def power_down(self):
        """Switches to IDLE mode (low power)."""
        r = self._read_reg(LIS2MDL_CFG_REG_A)
        r = (r & ~0b11) | 0b11  # MD1..0 = 11
        self._write_reg(LIS2MDL_CFG_REG_A, r)

    def wake(self, mode: str = "continuous"):
        """Wakes the sensor: 'continuous' (default) or 'single'."""
        md = {"continuous": 0b00, "single": 0b01}.get(mode, 0b00)
        r = self._read_reg(LIS2MDL_CFG_REG_A)
        r = (r & ~0b11) | md
        self._write_reg(LIS2MDL_CFG_REG_A, r)

    def soft_reset(self, wait_ms: int = 10):
        """
        SOFT_RST (bit5) in CFG_REG_A.
        The bit auto-clears; after reset, the sensor returns to default values (idle mode expected).
        """
        r = self._read_reg(LIS2MDL_CFG_REG_A)
        r |= 1 << 5  # SOFT_RST
        self._write_reg(LIS2MDL_CFG_REG_A, r)
        sleep_ms(wait_ms)

    def reboot(self, wait_ms: int = 10):
        """
        REBOOT (bit6) in CFG_REG_A: reload internal registers.
        The bit auto-clears.
        """
        r = self._read_reg(LIS2MDL_CFG_REG_A)
        r |= 1 << 6  # REBOOT
        self._write_reg(LIS2MDL_CFG_REG_A, r)
        sleep_ms(wait_ms)

    def is_idle(self) -> bool:
        """True if the sensor is in IDLE mode (MD1..0 == 11)."""
        return (self._read_reg(LIS2MDL_CFG_REG_A) & 0b11) == 0b11
