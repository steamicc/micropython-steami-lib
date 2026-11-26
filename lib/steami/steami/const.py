from collections import namedtuple

from micropython import const

# typing.NamedTuple does not exist in MicroPython.
Vector = namedtuple("Vector", ("x", "y", "z"))  # noqa: PYI024


class Release:
    """Board releases. The values are the texts used in messages."""

    UNKNOWN = ""
    V1A = "V1a"
    V1B = "V1b"
    V1C = "V1c"
    # Probing cannot tell V1a from V1b.
    V1AB = "V1a/V1b"


class Chip:
    """Chips of the internal I2C bus, with the names Arduino prints."""

    BME280 = "BME280"
    WSEN_HIDS = "WSEN-HIDS"
    WSEN_PADS = "WSEN-PADS"
    APDS9960 = "APDS-9960"
    VL53L1X = "VL53L1X"
    ISM330DL = "ISM330DL"
    LIS2MDL = "LIS2MDL"
    BQ27441 = "BQ27441"
    MCP23009E = "MCP23009E"


class Function:
    """Board functions, for Steami.has()."""

    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    PRESSURE = "pressure"
    DISTANCE = "distance"
    ACCELEROMETER = "accelerometer"
    GYROSCOPE = "gyroscope"
    MAGNETOMETER = "magnetometer"
    COMPASS = "compass"
    LIGHT = "light"
    COLOR = "color"
    GESTURE = "gesture"
    BATTERY = "battery"
    BUTTONS = "buttons"


class Status:
    """State of a chip or of a function."""

    OK = "ok"
    NOT_STARTED = "not started"
    NOT_RESPONDING = "not responding"
    NOT_ON_THIS_BOARD = "not on this board"
    UNKNOWN_BOARD = "unknown board"


class Origin:
    """How the release was found."""

    NONE = "none"
    FORCED = "forced"
    CONFIG = "config"
    PROBE = "probe"


# Message codes, as in Arduino (no E03, E30 or E31 here).
E_UNKNOWN_BOARD = "E01"
E_UNKNOWN_REVISION = "E02"
E_NOT_ANSWERING = "E10"
E_RELEASE_CONTRADICTED = "E11"
E_NOT_ON_THIS_BOARD = "E20"

# LIS2MDL min/max calibration: sampling rate and the largest sample count.
# After switching the accelerometer range, wait for two samples at 104 Hz so
# that no sample taken at the old range is read with the new scale.
ACCEL_SETTLE_MS = const(20)
MAG_CAL_SAMPLES_PER_SECOND = const(50)
MAG_CAL_SAMPLE_DELAY_MS = const(20)
MAG_CAL_MAX_SAMPLES = const(65535)

# I2C address of each chip on the internal bus.
ADDRESS = {
    Chip.BME280: const(0x76),
    Chip.WSEN_HIDS: const(0x5F),
    Chip.WSEN_PADS: const(0x5D),
    Chip.APDS9960: const(0x39),
    Chip.ISM330DL: const(0x6B),
    Chip.LIS2MDL: const(0x1E),
    Chip.VL53L1X: const(0x29),
    Chip.BQ27441: const(0x55),
    Chip.MCP23009E: const(0x20),
}

# Chips in the order of the Arduino enum, for printing.
CHIPS = (
    Chip.BME280,
    Chip.WSEN_HIDS,
    Chip.WSEN_PADS,
    Chip.APDS9960,
    Chip.ISM330DL,
    Chip.LIS2MDL,
    Chip.VL53L1X,
    Chip.BQ27441,
    Chip.MCP23009E,
)

# Driver of each chip: (module, class). The module is imported on first claim.
DRIVERS = {
    Chip.BME280: ("bme280", "BME280"),
    Chip.WSEN_HIDS: ("wsen_hids", "WSEN_HIDS"),
    Chip.WSEN_PADS: ("wsen_pads", "WSEN_PADS"),
    Chip.APDS9960: ("apds9960", "uAPDS9960"),  # the MicroPython I2C variant
    Chip.ISM330DL: ("ism330dl", "ISM330DL"),
    Chip.LIS2MDL: ("lis2mdl", "LIS2MDL"),
    Chip.VL53L1X: ("vl53l1x", "VL53L1X"),
    Chip.BQ27441: ("bq27441", "BQ27441"),
    Chip.MCP23009E: ("mcp23009e", "MCP23009E"),
}

# Chips that can serve each function: (V1a/V1b, V1c, unknown release), as in
# Arduino steamiRoute().
_ROUTES = {
    Function.TEMPERATURE: (
        (Chip.WSEN_HIDS, Chip.WSEN_PADS),
        (Chip.BME280,),
        (Chip.BME280, Chip.WSEN_HIDS, Chip.WSEN_PADS),
    ),
    Function.HUMIDITY: (
        (Chip.WSEN_HIDS,),
        (Chip.BME280,),
        (Chip.BME280, Chip.WSEN_HIDS),
    ),
    Function.PRESSURE: (
        (Chip.WSEN_PADS,),
        (Chip.BME280,),
        (Chip.BME280, Chip.WSEN_PADS),
    ),
    Function.DISTANCE: ((Chip.VL53L1X,),) * 3,
    Function.ACCELEROMETER: ((Chip.ISM330DL,),) * 3,
    Function.GYROSCOPE: ((Chip.ISM330DL,),) * 3,
    Function.MAGNETOMETER: ((Chip.LIS2MDL,),) * 3,
    Function.COMPASS: ((Chip.LIS2MDL,),) * 3,
    Function.LIGHT: ((Chip.APDS9960,), (), (Chip.APDS9960,)),
    Function.COLOR: ((Chip.APDS9960,), (), (Chip.APDS9960,)),
    Function.GESTURE: ((Chip.APDS9960,), (), (Chip.APDS9960,)),
    Function.BATTERY: ((Chip.BQ27441,),) * 3,
    Function.BUTTONS: ((Chip.MCP23009E,),) * 3,
}


def route(release, function):
    """Return the chips that can serve a function on a release, in order."""
    column = 1 if release == Release.V1C else 2 if release == Release.UNKNOWN else 0
    return _ROUTES[function][column]


# One chip ID read per entry, in probing order: (chip, register, IDs, release).
# Never 0x3B: that is the DAPLink bridge.
PROBES = (
    (Chip.BME280, const(0xD0), (0x60,), Release.V1C),
    (Chip.WSEN_HIDS, const(0x0F), (0xBC,), Release.V1AB),
    (Chip.WSEN_PADS, const(0x0F), (0xB3,), Release.V1AB),
    (Chip.APDS9960, const(0x92), (0xAB, 0x9C, 0xA8), Release.V1AB),
)

_RELEASE_OF_DIGIT = {1: Release.V1A, 2: Release.V1B, 3: Release.V1C}


def decode_revision(rev):
    """Decode a board revision code into (release, is_prototype), or None.

    Valid codes are 100..999 with generation 1 and release digit 1, 2 or 3
    (131 is generation 1, release 3, index 1). Index 0 is a prototype.
    """
    if not isinstance(rev, int) or isinstance(rev, bool) or rev < 100 or rev > 999:
        return None
    release = _RELEASE_OF_DIGIT.get((rev // 10) % 10)
    if rev // 100 != 1 or release is None:
        return None
    return release, rev % 10 == 0


# Buttons: a change is taken at once, then the bounces of the next 20 ms are ignored.
DEBOUNCE_MS = const(20)
POLL_MS = const(5)
