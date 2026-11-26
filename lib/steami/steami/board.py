from steami.const import (
    ADDRESS,
    CHIPS,
    DRIVERS,
    E_UNKNOWN_BOARD,
    E_UNKNOWN_REVISION,
    PROBES,
    Chip,
    Function,
    Origin,
    Release,
    Status,
    decode_revision,
    route,
)

_WHO = "SteamiBoard"

_UNKNOWN_BOARD = (
    "cannot tell which STeaMi this is: no V1a/V1b or V1c sensor answered. "
    'Call Steami.begin("V1c") (or "V1b", "V1a") at the start of the program.'
)
_UNKNOWN_REVISION = (
    "unknown board revision {} in the board config. Update the STeaMi library; "
    "the board is detected from its sensors instead."
)

_FUNCTIONS = tuple(getattr(Function, n) for n in dir(Function) if not n.startswith("_"))
_FORCEABLE = (Release.V1A, Release.V1B, Release.V1C)


class _Board(object):
    """The STeaMi board: release detection, shared bus and messages.

    Use the shared instance ``Steami``. Creating it touches no hardware.
    """

    def __init__(self):
        self.end()

    def end(self):
        """Forget everything: release, drivers and messages already sent."""
        self._i2c = None
        self._bridge = None
        self._config = None
        self._config_tried = False
        self._detected = False
        self._release = Release.UNKNOWN
        self._origin = Origin.NONE
        self._revision = None
        self._probed_chip = None
        self._drivers = {}  # chip -> driver, or None when it did not answer
        self._calibration_tried = []
        self._calibration_applied = []
        self._banner_delivered = False
        self._reported = []
        self._last_error = ""
        self._logger = print

    # --------------------------------------------------
    # Messages
    # --------------------------------------------------

    def set_logger(self, fn):
        """Send messages to fn(line), or nowhere with None. Default: print."""
        self._logger = fn

    def last_error(self):
        """Return the last message, even when it was not printed."""
        return self._last_error

    def report(self, who, code, detail):
        """Report "[STeaMi] <who>: <detail> (<code>)", once per (who, code)."""
        line = "[STeaMi] {}: {} ({})".format(who, detail, code)
        self._last_error = line
        key = (who, code)
        if key in self._reported:
            return
        self._reported.append(key)
        self._deliver(line)

    def _deliver(self, line):
        if self._logger is not None:
            self._logger(line)

    # --------------------------------------------------
    # Shared resources
    # --------------------------------------------------

    def i2c(self):
        """Return the internal I2C bus, created on first call."""
        if self._i2c is None:
            from machine import I2C

            self._i2c = I2C(1)
        return self._i2c

    def config(self):
        """Return the SteamiConfig of the board, or None without a config zone."""
        self._load_config()
        return self._config

    def _load_config(self):
        if self._config_tried:
            return
        self._config_tried = True
        try:
            if self._bridge is None:
                from daplink_bridge.device import DaplinkBridge

                self._bridge = DaplinkBridge(self.i2c())
            # Older DAPLink firmwares lock up on config commands: probe first.
            if not self._bridge.has_config_zone():
                return
            from steami_config.device import SteamiConfig

            config = SteamiConfig(self._bridge)
            config.load()
            _ = config.board_revision  # fails here if the JSON is not an object
            self._config = config
        except Exception:
            # No bridge or a bad config: the board is detected by probing.
            self._config = None

    # --------------------------------------------------
    # Chips
    # --------------------------------------------------

    def claim(self, chip):
        """Create the shared driver of a chip once; return Status.OK or NOT_RESPONDING.

        The answer is kept: a chip that did not answer is not tried again
        before end().
        """
        if chip not in DRIVERS:
            return Status.NOT_RESPONDING
        if chip not in self._drivers:
            self.begin()
            self._drivers[chip] = self._build(chip)
        return Status.OK if self._drivers[chip] is not None else Status.NOT_RESPONDING

    def _build(self, chip):
        module, name = DRIVERS[chip]
        try:
            cls = getattr(__import__(module), name)
            if chip == Chip.MCP23009E:
                from machine import Pin

                driver = cls(self.i2c(), ADDRESS[chip], Pin("RST_EXPANDER", Pin.OUT))
                # Its constructor makes no transfer: probe the address (ACK).
                self.i2c().writeto(ADDRESS[chip], b"")
                return driver
            return cls(self.i2c())
        except Exception:
            # Each driver raises its own exception (or OSError) when the chip is absent.
            return None

    def _driver(self, chip):
        self.claim(chip)
        return self._drivers[chip]

    def bme280(self):
        return self._driver(Chip.BME280)

    def wsen_hids(self):
        return self._driver(Chip.WSEN_HIDS)

    def wsen_pads(self):
        return self._driver(Chip.WSEN_PADS)

    def apds9960(self):
        return self._driver(Chip.APDS9960)

    def vl53l1x(self):
        return self._driver(Chip.VL53L1X)

    def ism330dl(self):
        return self._driver(Chip.ISM330DL)

    def lis2mdl(self):
        return self._driver(Chip.LIS2MDL)

    def bq27441(self):
        return self._driver(Chip.BQ27441)

    def mcp23009e(self):
        return self._driver(Chip.MCP23009E)

    def has(self, function):
        """Return True when this release has a chip for the function."""
        return len(route(self.release(), function)) > 0

    # --------------------------------------------------
    # Calibration
    # --------------------------------------------------

    def calibrated(self, chip):
        """Return True when a stored calibration was applied to the chip."""
        return chip in self._calibration_applied

    def calibrate(self, chip):
        """Apply the stored calibration to a chip, once. Return True if applied."""
        if self.claim(chip) != Status.OK:
            return False
        if chip in self._calibration_tried:
            return self.calibrated(chip)
        self._calibration_tried.append(chip)  # a failing config read is not retried
        if chip not in (
            Chip.BME280,
            Chip.WSEN_HIDS,
            Chip.WSEN_PADS,
            Chip.ISM330DL,
            Chip.LIS2MDL,
        ):
            return False
        config = self.config()
        if config is None:
            return False
        driver = self._drivers[chip]
        try:
            applied = self._apply(config, chip, driver)
        except Exception:
            applied = False  # a malformed calibration entry
        if applied:
            self._calibration_applied.append(chip)
        return applied

    @staticmethod
    def _apply(config, chip, driver):
        if chip == Chip.ISM330DL:
            if config.get_accelerometer_calibration() is None:
                return False
            config.apply_accelerometer_calibration(driver)
        elif chip == Chip.LIS2MDL:
            if config.get_magnetometer_calibration() is None:
                return False
            config.apply_magnetometer_calibration(driver)
        else:
            name = type(driver).__name__.lower()
            cal = config.get_temperature_calibration(name)
            if chip == Chip.WSEN_HIDS and (
                cal is None or (cal["gain"] == 1.0 and cal["offset"] == 0.0)
            ):
                # The tool of steami_config stores the real calibration under
                # "hts" (HTS221 driver); "hid" is the identity Arduino reads.
                legacy = config.get_temperature_calibration("hts221")
                if legacy is not None:
                    cal = legacy
            if cal is None:
                return False
            driver._temp_gain = cal["gain"]
            driver._temp_offset = cal["offset"]
        return True

    # --------------------------------------------------
    # Diagnostics
    # --------------------------------------------------

    def print_info(self):
        """Send the board line, then one line per chip of this release."""
        self.begin()
        if not self._banner_delivered:
            self._log_banner()
        for chip in CHIPS:
            if not any(chip in route(self._release, f) for f in _FUNCTIONS):
                continue
            if chip not in self._drivers:
                state = "not tried"
            elif self._drivers[chip] is None:
                state = "not responding"
            else:
                state = "OK"
            self._deliver(
                "{} 0x{:02X} {}{}".format(
                    chip, ADDRESS[chip], state, ", calibrated" if self.calibrated(chip) else ""
                )
            )

    # --------------------------------------------------
    # Release
    # --------------------------------------------------

    def begin(self, release=None):
        """Detect the release once and return it.

        With "V1a", "V1b" or "V1c", skip detection (no I2C traffic); this
        overrides a release already found. Without it, detection runs once.
        """
        if release == Release.UNKNOWN:
            release = None
        if release is not None and release not in _FORCEABLE:
            raise ValueError("release must be V1a, V1b or V1c")
        if release is not None:
            changed = not self._detected or self._release != release
            changed = changed or self._origin != Origin.FORCED
            self._detected = True
            self._release = release
            self._origin = Origin.FORCED
            if changed:
                self._log_banner()
            return self._release
        if self._detected:
            return self._release
        self._detected = True
        if not self._detect_from_config() and not self._detect_by_probe():
            self._release = Release.UNKNOWN
            self._origin = Origin.NONE
            self.report(_WHO, E_UNKNOWN_BOARD, _UNKNOWN_BOARD)
        self._log_banner()
        return self._release

    def release(self):
        """Return the release (Release.*), detecting it on first use."""
        return self.begin()

    def release_name(self):
        """Return the release as a text, "unknown" when not found."""
        return self.release() or "unknown"

    def origin(self):
        """Return how the release was found (Origin.*)."""
        self.begin()
        return self._origin

    def revision(self):
        """Return the revision code read from the board config, or None."""
        self.begin()
        return self._revision

    def is_prototype(self):
        """Return True when the board config says this is a prototype."""
        self.begin()
        info = decode_revision(self._revision)
        return info is not None and info[1]

    def is_v1c(self):
        return self.release() == Release.V1C

    def is_v1ab(self):
        return self.release() in (Release.V1A, Release.V1B, Release.V1AB)

    def _detect_from_config(self):
        config = self.config()
        if config is None:
            return False
        rev = config.board_revision
        if rev is None:
            return False  # no revision written: probe, without a message
        self._revision = rev
        info = decode_revision(rev)
        if info is None:
            self.report(_WHO, E_UNKNOWN_REVISION, _UNKNOWN_REVISION.format(rev))
            return False
        self._release = info[0]
        self._origin = Origin.CONFIG
        return True

    def _detect_by_probe(self):
        for chip, reg, ids, release in PROBES:
            try:
                data = self.i2c().readfrom_mem(ADDRESS[chip], reg, 1)
            except OSError:
                continue
            if len(data) == 1 and data[0] in ids:
                self._release = release
                self._origin = Origin.PROBE
                self._probed_chip = chip
                return True
        return False

    def _log_banner(self):
        name = self._release or "unknown"
        origin = self._origin
        if origin == Origin.FORCED:
            text = "forced by Steami.begin()"
        elif origin == Origin.CONFIG:
            text = "read from the board config, revision {}{}".format(
                self._revision, ", prototype" if decode_revision(self._revision)[1] else ""
            )
        elif origin == Origin.PROBE:
            text = "detected: {} at 0x{:02X}".format(self._probed_chip, ADDRESS[self._probed_chip])
        else:
            text = "nothing detected"
        self._banner_delivered = self._logger is not None
        self._deliver("[STeaMi] Board {} ({})".format(name, text))


Steami = _Board()
