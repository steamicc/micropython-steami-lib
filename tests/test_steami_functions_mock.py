"""Tests of the STeaMi function classes (steami.handle and one module per function)."""

import math

import pytest

from tests.fake_machine import FakePin, steami_chips
from tests.fake_machine.i2c_bus import FakeI2CBus
from tests.fake_machine.mcp23009 import ADDR as MCP_ADDR
from tests.fake_machine.mcp23009 import DOWN, GPPU, IODIR, LEFT, RIGHT, UP, FakeMCP23009
from tests.test_steami_board_mock import (  # noqa: F401 (board_module is a fixture)
    Setup,
    board_module,
    calibration,
)

V1AB = "V1a/V1b"
HINT = "Check the board or try another one."


class Board(Setup):
    """A board under test whose log holds every bus transfer, not only readfrom_mem."""

    def __init__(self, module, release="V1c", **kwargs):
        super().__init__(module, release, **kwargs)
        for name in ("readfrom_mem_into", "readfrom", "writeto", "writeto_mem", "writevto"):
            self._log(name)

    def _log(self, name):
        method = getattr(self.bus, name)

        def logged(addr, *args, **kwargs):
            self.reads.append((addr, name))
            return method(addr, *args, **kwargs)

        setattr(self.bus, name, logged)

    def messages(self):
        """The coded lines, without the board banner."""
        return [line for line in self.lines if not line.startswith("[STeaMi] Board")]


@pytest.fixture
def steami(board_module):  # noqa: F811 (the imported fixture)
    """The board module, the const module and the function classes."""
    from steami.accelerometer import Accelerometer
    from steami.battery import Battery
    from steami.buttons import Buttons
    from steami.color import Color
    from steami.compass import Compass
    from steami.distance import Distance
    from steami.gesture import Gesture
    from steami.gyroscope import Gyroscope
    from steami.handle import Handle
    from steami.humidity import Humidity
    from steami.light import Light
    from steami.magnetometer import Magnetometer
    from steami.pressure import Pressure
    from steami.temperature import Temperature

    yield {
        "board": board_module,
        "const": board_module[1],
        "Handle": Handle,
        "Battery": Battery,
        "Distance": Distance,
        "Temperature": Temperature,
        "Humidity": Humidity,
        "Pressure": Pressure,
        "Accelerometer": Accelerometer,
        "Gyroscope": Gyroscope,
        "Magnetometer": Magnetometer,
        "Compass": Compass,
        "Light": Light,
        "Color": Color,
        "Gesture": Gesture,
        "Buttons": Buttons,
    }


def board(steami, release="V1c", config="", zone=False, **kwargs):
    """A board found by probing, unless a config is given."""
    return Board(steami["board"], release, config=config, zone=zone, **kwargs)


def unknown_release(steami, present=()):
    """A board whose release cannot be found, with some environment chips still answering.

    The probing reads of the chips in `present` get a wrong ID once, so that
    detection fails while their drivers start normally afterwards.
    """
    missing = tuple(c for c in ("WSEN-HIDS", "WSEN-PADS") if c not in present)
    s = Board(steami["board"], V1AB, missing=(*missing, "APDS-9960"), config="", zone=False)
    if "BME280" in present:
        s.bus._devices[0x76] = FakeI2CBus({0x76: steami_chips.image("BME280")})._devices[0x76]
    for chip in present:
        reg = 0xD0 if chip == "BME280" else 0x0F
        s.bus.set_register_sequence(steami_chips.ADDRESS[chip], reg, [b"\x00"])
    assert s.steami.begin() == ""
    s.reads.clear()
    return s


def first_contacts(s):
    """The addresses in the order they were first used on the bus."""
    order = []
    for addr, _ in s.reads:
        if addr not in order:
            order.append(addr)
    return order


# --------------------------------------------------
# Routing
# --------------------------------------------------


@pytest.mark.parametrize(
    ("cls", "release", "missing", "chip"),
    [
        ("Temperature", "V1c", (), "BME280"),
        ("Temperature", V1AB, (), "WSEN-HIDS"),
        ("Temperature", V1AB, ("WSEN-HIDS",), "WSEN-PADS"),
        ("Humidity", "V1c", (), "BME280"),
        ("Humidity", V1AB, (), "WSEN-HIDS"),
        ("Pressure", "V1c", (), "BME280"),
        ("Pressure", V1AB, (), "WSEN-PADS"),
    ],
)
def test_mock_routing(steami, cls, release, missing, chip):
    board(steami, release, missing=missing)
    handle = steami[cls]()
    assert handle.chip() == ""
    assert handle.begin() is True
    assert handle.chip() == chip
    assert handle.is_available() is True
    assert handle.status() == steami["const"].Status.OK
    assert handle.error() == ""


@pytest.mark.parametrize(
    ("cls", "present", "chip", "tried"),
    [
        ("Temperature", ("BME280", "WSEN-HIDS", "WSEN-PADS"), "BME280", [0x76]),
        ("Temperature", ("WSEN-HIDS", "WSEN-PADS"), "WSEN-HIDS", [0x76, 0x5F]),
        ("Temperature", ("WSEN-PADS",), "WSEN-PADS", [0x76, 0x5F, 0x5D]),
        ("Humidity", ("BME280",), "BME280", [0x76]),
        ("Humidity", ("WSEN-HIDS",), "WSEN-HIDS", [0x76, 0x5F]),
        ("Pressure", ("BME280",), "BME280", [0x76]),
        ("Pressure", ("WSEN-PADS",), "WSEN-PADS", [0x76, 0x5D]),
    ],
)
def test_mock_routing_unknown_release(steami, cls, present, chip, tried):
    s = unknown_release(steami, present)
    handle = steami[cls]()
    assert handle.begin() is True
    assert handle.chip() == chip
    # Candidates are tried in the order of the table.
    assert first_contacts(s) == tried


# --------------------------------------------------
# Reads
# --------------------------------------------------


def expected(chip, method, *args):
    """What the chip's own driver computes from the same register image."""
    import bme280
    import wsen_hids
    import wsen_pads

    cls = {
        "BME280": bme280.BME280,
        "WSEN-HIDS": wsen_hids.WSEN_HIDS,
        "WSEN-PADS": wsen_pads.WSEN_PADS,
    }[chip]
    release = "V1c" if chip == "BME280" else V1AB
    return getattr(cls(steami_chips.board(release)), method)(*args)


@pytest.mark.parametrize(
    ("cls", "release", "missing", "chip", "method"),
    [
        ("Temperature", "V1c", (), "BME280", "temperature"),
        ("Temperature", V1AB, (), "WSEN-HIDS", "temperature"),
        ("Temperature", V1AB, ("WSEN-HIDS",), "WSEN-PADS", "temperature"),
        ("Humidity", "V1c", (), "BME280", "humidity"),
        ("Humidity", V1AB, (), "WSEN-HIDS", "humidity"),
        ("Pressure", "V1c", (), "BME280", "pressure_hpa"),
        ("Pressure", V1AB, (), "WSEN-PADS", "pressure_hpa"),
    ],
)
def test_mock_read(steami, cls, release, missing, chip, method):
    board(steami, release, missing=missing)
    value = steami[cls]().read()
    assert value == pytest.approx(expected(chip, method))
    assert not math.isnan(value)


def test_mock_read_values_are_plausible(steami):
    board(steami)
    assert 10 < steami["Temperature"]().read() < 40
    assert 0 < steami["Humidity"]().read() < 100
    assert 900 < steami["Pressure"]().read() < 1100


def test_mock_altitude_bme280(steami):
    board(steami)
    pressure = steami["Pressure"]()
    assert pressure.altitude() == pytest.approx(expected("BME280", "altitude"))


def test_mock_altitude_wsen_pads(steami):
    board(steami, V1AB)
    p = expected("WSEN-PADS", "pressure_hpa")
    assert steami["Pressure"]().altitude(1000.0) == pytest.approx(
        44330.0 * (1.0 - (p / 1000.0) ** 0.1903)
    )


def test_mock_altitude_absent(steami):
    board(steami, missing=("BME280",))
    pressure = steami["Pressure"]()
    assert math.isnan(pressure.altitude())
    board(steami)
    pressure = steami["Pressure"]()
    assert math.isnan(pressure.altitude(0))
    assert math.isnan(pressure.altitude(-5))


def test_mock_set_offset_adds_to_calibrated_reading(steami):
    s = board(steami, config=calibration(bme={"g": 1.0, "o": -0.5}), zone=True)
    temperature = steami["Temperature"]()
    raw = expected("BME280", "temperature")
    assert temperature.read() == pytest.approx(raw - 0.5)
    assert s.steami.calibrated("BME280") is True
    temperature.set_offset(2)
    assert temperature.read() == pytest.approx(raw + 1.5)
    # The offset belongs to this object: the shared driver is not changed.
    assert steami["Temperature"]().read() == pytest.approx(raw - 0.5)


def test_mock_failed_read_returns_nan(steami):
    s = board(steami, V1AB)
    temperature = steami["Temperature"]()
    humidity = steami["Humidity"]()
    pressure = steami["Pressure"]()
    assert temperature.begin() and humidity.begin() and pressure.begin()
    # The chips stop answering after begin(): the drivers raise their own errors.
    del s.bus._devices[0x5F]
    del s.bus._devices[0x5D]
    assert math.isnan(temperature.read())
    assert math.isnan(humidity.read())
    assert math.isnan(pressure.read())
    assert math.isnan(pressure.altitude())
    assert temperature.status() == steami["const"].Status.OK


# --------------------------------------------------
# Absence and messages
# --------------------------------------------------


@pytest.mark.parametrize(
    ("cls", "chip", "address", "noun"),
    [
        ("Temperature", "BME280", 0x76, "temperature sensor"),
        ("Humidity", "BME280", 0x76, "humidity sensor"),
        ("Pressure", "BME280", 0x76, "pressure sensor"),
    ],
)
def test_mock_absent_e10(steami, cls, chip, address, noun):
    # Found by probing the BME280's ID; then the chip stops answering.
    s = board(steami)
    assert s.steami.begin() == "V1c"
    del s.bus._devices[0x76]
    handle = steami[cls]()
    assert handle.begin() is False
    const = steami["const"]
    assert handle.status() == const.Status.NOT_RESPONDING
    assert handle.error() == "no answer"
    assert handle.is_available() is False
    assert handle.chip() == ""
    assert math.isnan(handle.read())
    assert s.messages() == [
        "[STeaMi] {}: the {} {} (I2C 0x{:02X}) did not answer. {} (E10)".format(
            cls, chip, noun, address, HINT
        )
    ]


def test_mock_absent_several_candidates_e10(steami):
    s = board(steami, V1AB, missing=("WSEN-HIDS", "WSEN-PADS"))
    temperature = steami["Temperature"]()
    assert math.isnan(temperature.read())
    assert s.messages() == [
        "[STeaMi] Temperature: no temperature sensor answered (WSEN-HIDS, WSEN-PADS). "
        + HINT
        + " (E10)"
    ]


def test_mock_absent_unknown_release_e10(steami):
    s = unknown_release(steami)
    s.lines.clear()
    assert steami["Temperature"]().begin() is False
    assert steami["Humidity"]().begin() is False
    assert steami["Pressure"]().begin() is False
    assert s.messages() == [
        "[STeaMi] Temperature: no temperature sensor answered (BME280, WSEN-HIDS, WSEN-PADS). "
        + HINT
        + " (E10)",
        "[STeaMi] Humidity: no humidity sensor answered (BME280, WSEN-HIDS). " + HINT + " (E10)",
        "[STeaMi] Pressure: no pressure sensor answered (BME280, WSEN-PADS). " + HINT + " (E10)",
    ]


def test_mock_message_once_per_class(steami):
    s = board(steami, V1AB, missing=("WSEN-HIDS", "WSEN-PADS"))
    for _ in range(3):
        assert steami["Temperature"]().begin() is False
    assert len(s.messages()) == 1


def test_mock_e11_forced(steami):
    s = board(steami, V1AB)
    s.steami.begin("V1c")
    temperature = steami["Temperature"]()
    assert temperature.begin() is False
    assert temperature.status() == steami["const"].Status.NOT_RESPONDING
    assert temperature.error() == "no answer"
    assert s.messages() == [
        (
            "[STeaMi] Temperature: this STeaMi is set as a V1c (forced by Steami.begin()), but its "
            "BME280 temperature sensor (I2C 0x76) did not answer. Check Steami.begin() or the board "
            "config. (E11)"
        )
    ]


def test_mock_e11_forced_names_the_first_candidate(steami):
    s = board(steami)
    s.steami.begin("V1a")
    assert steami["Temperature"]().begin() is False
    assert s.messages() == [
        (
            "[STeaMi] Temperature: this STeaMi is set as a V1a (forced by Steami.begin()), but its "
            "WSEN-HIDS temperature sensor (I2C 0x5F) did not answer. Check Steami.begin() or the "
            "board config. (E11)"
        )
    ]


def test_mock_e11_config(steami):
    s = board(steami, V1AB, config='{"rev": 131}', zone=True)
    assert steami["Humidity"]().begin() is False
    assert s.messages() == [
        (
            "[STeaMi] Humidity: this STeaMi is set as a V1c (read from the board config), but its "
            "BME280 humidity sensor (I2C 0x76) did not answer. Check Steami.begin() or the board "
            "config. (E11)"
        )
    ]


def test_mock_probe_origin_gives_e10_not_e11(steami):
    s = board(steami, V1AB, missing=("WSEN-PADS",))
    assert s.steami.origin() == steami["const"].Origin.PROBE
    assert steami["Pressure"]().begin() is False
    assert s.messages() == [
        "[STeaMi] Pressure: the WSEN-PADS pressure sensor (I2C 0x5D) did not answer. "
        + HINT
        + " (E10)"
    ]


class _Handles:
    """Handles of functions that Task 5 has no class for, to reach every branch of Handle."""

    @staticmethod
    def distance(steami):
        class Distance(steami["Handle"]):
            _NOUN = "distance sensor"

            def __init__(self):
                super().__init__(steami["const"].Function.DISTANCE)

        return Distance()

    @staticmethod
    def light(steami):
        class Light(steami["Handle"]):
            _NOUN = "light sensor"
            _FALLBACK = "read() will return 0."

            def __init__(self):
                super().__init__(steami["const"].Function.LIGHT)

        return Light()


def test_mock_forced_but_same_chip_on_every_release_gives_e10(steami):
    s = board(steami, missing=("VL53L1X",))
    s.steami.begin("V1c")
    distance = _Handles.distance(steami)
    assert distance.begin() is False
    assert s.messages() == [
        "[STeaMi] Distance: the VL53L1X distance sensor (I2C 0x29) did not answer. "
        + HINT
        + " (E10)"
    ]


def test_mock_not_on_this_board_e20(steami):
    s = board(steami)
    light = _Handles.light(steami)
    assert light.begin() is False
    assert light.status() == steami["const"].Status.NOT_ON_THIS_BOARD
    assert light.error() == "not on this board"
    assert light._driver() is None
    assert s.messages() == [
        (
            "[STeaMi] Light: this STeaMi is a V1c, it has no light sensor (APDS-9960 is on V1a/V1b "
            "only). read() will return 0. (E20)"
        )
    ]


def test_mock_driver_is_the_shared_one(steami):
    s = board(steami)
    temperature = steami["Temperature"]()
    assert temperature._driver() is s.steami.bme280()
    assert temperature.status() == steami["const"].Status.OK


# --------------------------------------------------
# Bus traffic
# --------------------------------------------------


@pytest.mark.parametrize("cls", ["Temperature", "Humidity", "Pressure"])
def test_mock_no_retry_after_failed_begin(steami, cls):
    s = board(steami, missing=("BME280",))
    handle = steami[cls]()
    assert handle.begin() is False
    reads, lines = len(s.reads), list(s.lines)
    claims = []
    claim = s.steami.claim
    s.steami.claim = lambda chip: claims.append(chip) or claim(chip)
    for _ in range(10):
        assert math.isnan(handle.read())
    assert handle.begin() is False
    assert len(s.reads) == reads
    assert s.lines == lines
    # The handle itself does not try again (the board would answer from its cache).
    assert claims == []


def test_mock_no_bus_access_before_first_read(steami):
    s = board(steami)
    temperature = steami["Temperature"]()
    humidity = steami["Humidity"]()
    pressure = steami["Pressure"]()
    temperature.set_offset(1.0)
    assert temperature.status() == steami["const"].Status.NOT_STARTED
    assert temperature.error() == "not started"
    assert temperature.is_available() is False
    assert temperature.chip() == ""
    assert humidity.chip() == pressure.chip() == ""
    assert s.reads == []
    assert s.lines == []
    temperature.read()
    assert s.reads != []
    assert temperature.status() == steami["const"].Status.OK


def test_mock_begin_is_idempotent(steami):
    s = board(steami)
    temperature = steami["Temperature"]()
    assert temperature.begin() is True
    reads = len(s.reads)
    assert temperature.begin() is True
    assert len(s.reads) == reads


# --------------------------------------------------
# Errors inside reads
# --------------------------------------------------


def probe(steami, method, *args):
    """A temperature handle whose read() is _read(nan, method, *args)."""

    class Probe(steami["Handle"]):
        _NOUN = "temperature sensor"

        def __init__(self):
            super().__init__(steami["const"].Function.TEMPERATURE)

        def read(self):
            return self._read(float("nan"), method, *args)

    return Probe()


def test_mock_read_misspelt_method_raises(steami):
    board(steami)
    handle = probe(steami, "temprature")
    with pytest.raises(AttributeError):
        handle.read()
    assert handle.status() == steami["const"].Status.OK


def test_mock_read_wrong_argument_count_raises(steami):
    board(steami)
    with pytest.raises(TypeError):
        probe(steami, "temperature", 1).read()


def test_mock_read_driver_exception_gives_absent_value(steami):
    from wsen_hids.exceptions import WSENHIDSError

    s = board(steami, V1AB)
    humidity = steami["Humidity"]()
    assert humidity.begin() is True
    del s.bus._devices[0x5F]
    # The driver raises its own class, an OSError subclass (#320).
    with pytest.raises(WSENHIDSError) as info:
        s.steami.wsen_hids().humidity()
    assert isinstance(info.value, OSError)
    assert math.isnan(humidity.read())


def test_mock_read_with_a_function(steami):
    s = board(steami)
    assert probe(steami, lambda d, k: d.temperature() * k, 2).read() == pytest.approx(
        2 * expected("BME280", "temperature")
    )
    # Same policy as a method name: driver errors give the absent value...
    del s.bus._devices[0x76]
    assert math.isnan(probe(steami, lambda d: d.pressure_hpa()).read())
    # ...programming errors propagate.
    with pytest.raises(AttributeError):
        probe(steami, lambda d: d.no_such_method()).read()
    with pytest.raises(TypeError):
        probe(steami, lambda d: d.temperature(), 1).read()


# --------------------------------------------------
# Distance and Battery
# --------------------------------------------------


def test_mock_distance_read_and_cm(steami):
    s = board(steami)
    distance = steami["Distance"]()
    assert distance.read() == 250
    assert isinstance(distance.read(), int)
    assert distance.cm() == pytest.approx(25.0)
    assert distance.chip() == "VL53L1X"
    assert s.messages() == []


def test_mock_distance_is_the_same_on_every_release(steami):
    board(steami, V1AB)
    assert steami["Distance"]().read() == 250


def test_mock_distance_begin_starts_ranging_once(steami):
    s = board(steami)
    s.steami.claim("VL53L1X")  # the driver exists; the function has not started it
    s.bus.clear_write_log()
    distance = steami["Distance"]()
    assert s.bus.get_write_log() == []
    assert distance.begin() is True
    start = (0x29, 0x0087, b"\x40")
    assert s.bus.get_write_log().count(start) == 1
    distance.begin()
    distance.read()
    assert s.bus.get_write_log().count(start) == 1


def test_mock_distance_zero_means_no_target(steami):
    s = board(steami)
    distance = steami["Distance"]()
    assert distance.begin() is True
    s.bus._devices[0x29][0x0089] = bytes(17)
    assert distance.read() == -1
    assert math.isnan(distance.cm())


def test_mock_distance_absent(steami):
    s = board(steami, missing=("VL53L1X",))
    distance = steami["Distance"]()
    assert distance.read() == -1
    assert math.isnan(distance.cm())
    assert distance.status() == steami["const"].Status.NOT_RESPONDING
    assert s.messages() == [
        "[STeaMi] Distance: the VL53L1X distance sensor (I2C 0x29) did not answer. "
        + HINT
        + " (E10)"
    ]


def test_mock_distance_failed_read(steami):
    s = board(steami)
    distance = steami["Distance"]()
    assert distance.begin() is True
    del s.bus._devices[0x29]
    assert distance.read() == -1
    assert math.isnan(distance.cm())


def test_mock_battery_reads(steami):
    s = board(steami)
    battery = steami["Battery"]()
    assert battery.percent() == 92
    assert isinstance(battery.percent(), int)
    assert battery.voltage() == pytest.approx(3.7)
    assert battery.current() == 50
    assert isinstance(battery.current(), int)
    assert battery.is_charging() is True
    assert battery.chip() == "BQ27441"
    assert s.messages() == []


@pytest.mark.parametrize(
    ("raw", "charging"), [(b"\xce\xff", False), (b"\x00\x00", False), (b"\x01\x00", True)]
)
def test_mock_battery_is_charging_follows_the_sign_of_the_current(steami, raw, charging):
    s = board(steami)
    battery = steami["Battery"]()
    assert battery.begin() is True
    s.bus._devices[0x55][0x10] = raw
    assert battery.is_charging() is charging
    if raw == b"\xce\xff":
        assert battery.current() == -50


def test_mock_battery_zero_voltage_is_nan(steami):
    s = board(steami)
    battery = steami["Battery"]()
    assert battery.begin() is True
    s.bus._devices[0x55][0x04] = b"\x00\x00"
    assert math.isnan(battery.voltage())


def test_mock_battery_absent(steami):
    s = board(steami, missing=("BQ27441",))
    battery = steami["Battery"]()
    assert battery.percent() == 0
    assert math.isnan(battery.voltage())
    assert battery.current() == 0
    assert battery.is_charging() is False
    assert s.messages() == [
        (
            "[STeaMi] Battery: the BQ27441 battery gauge (I2C 0x55) did not answer. "
            "Plug in a battery, then reset the board. (E10)"
        )
    ]


def test_mock_battery_failed_read(steami):
    s = board(steami)
    battery = steami["Battery"]()
    assert battery.begin() is True
    del s.bus._devices[0x55]
    assert battery.percent() == 0
    assert math.isnan(battery.voltage())
    assert battery.current() == 0
    assert battery.is_charging() is False


# --------------------------------------------------
# Accelerometer, Gyroscope, Magnetometer and Compass
# --------------------------------------------------

CTRL1_XL = (0x6B, 0x10)


def set_raw(s, addr, reg, *values):
    """Put signed 16-bit values (little endian) in consecutive registers of a chip."""
    s.bus._devices[addr][reg] = b"".join(v.to_bytes(2, "little", signed=True) for v in values)


def set_field(s, x, y, z=0):
    """The raw magnetic field of the LIS2MDL, in LSB."""
    set_raw(s, 0x1E, 0xE8, x, y, z)


def nan_vector(vector):
    return all(math.isnan(v) for v in vector)


def test_mock_vector_is_a_namedtuple(steami):
    vector = steami["const"].Vector(1, 2, 3)
    assert (vector.x, vector.y, vector.z) == (1, 2, 3)
    assert tuple(vector) == (1, 2, 3)
    assert steami["const"].Vector._fields == ("x", "y", "z")


def test_mock_accelerometer_and_gyroscope_share_one_driver(steami):
    s = board(steami)
    accelerometer, gyroscope = steami["Accelerometer"](), steami["Gyroscope"]()
    assert accelerometer.begin() is True
    assert gyroscope.begin() is True
    assert accelerometer._driver() is gyroscope._driver() is s.steami.ism330dl()
    assert accelerometer.chip() == gyroscope.chip() == "ISM330DL"


def test_mock_accelerometer_begin_sets_8g_at_104hz(steami):
    s = board(steami)
    accelerometer = steami["Accelerometer"]()
    s.bus.clear_write_log()
    assert accelerometer.begin() is True
    # CTRL1_XL = ODR 104 Hz (0x4) << 4 | FS +-8 g (0b11) << 2
    writes = [w for w in s.bus.get_write_log() if w[:2] == CTRL1_XL]
    assert writes[-1] == (*CTRL1_XL, b"\x4c")
    accelerometer.begin()
    accelerometer.read()
    assert [w for w in s.bus.get_write_log() if w[:2] == CTRL1_XL] == writes


def test_mock_accelerometer_begin_waits_for_a_sample_at_8g(steami, monkeypatch):
    # The output registers keep the last +-2 g sample until the sensor takes
    # the next one, about 10 ms at 104 Hz: begin() waits so that the first
    # read is not converted with the wrong scale (4 times too large).
    import steami.accelerometer as accelerometer_module

    board(steami)
    events = []
    monkeypatch.setattr(accelerometer_module, "sleep_ms", events.append)
    accelerometer = steami["Accelerometer"]()
    assert accelerometer.begin() is True
    assert events == [20]
    accelerometer.begin()
    accelerometer.read()
    assert events == [20]


def test_mock_accelerometer_absent_does_not_wait(steami, monkeypatch):
    import steami.accelerometer as accelerometer_module

    board(steami, missing=("ISM330DL",))
    events = []
    monkeypatch.setattr(accelerometer_module, "sleep_ms", events.append)
    assert steami["Accelerometer"]().begin() is False
    assert events == []


def test_mock_gyroscope_does_not_change_the_accelerometer_range(steami):
    s = board(steami)
    gyroscope = steami["Gyroscope"]()
    assert gyroscope.begin() is True
    assert (*CTRL1_XL, b"\x4c") not in s.bus.get_write_log()


def test_mock_accelerometer_reads_g(steami):
    s = board(steami)
    accelerometer = steami["Accelerometer"]()
    set_raw(s, 0x6B, 0x28, 4096, -8192, 16384)
    vector = accelerometer.read()
    assert vector == pytest.approx((0.999424, -1.998848, 3.997696), abs=1e-6)  # 0.244 mg/LSB
    assert (accelerometer.x(), accelerometer.y(), accelerometer.z()) == pytest.approx(
        tuple(vector)
    )
    assert vector.x == vector[0]
    assert accelerometer.strength() == pytest.approx(math.sqrt(sum(v * v for v in vector)))
    assert accelerometer.chip() == "ISM330DL"
    assert s.messages() == []


def test_mock_accelerometer_includes_the_driver_offset(steami):
    s = board(steami)
    accelerometer = steami["Accelerometer"]()
    set_raw(s, 0x6B, 0x28, 0, 0, 4096)
    s.steami.ism330dl().set_accel_offset(0.0, 0.0, 0.25)
    assert accelerometer.z() == pytest.approx(0.999424 - 0.25)


@pytest.mark.parametrize(
    ("raw", "g", "shaken"),
    [((0, 0, 4096), None, False), ((0, 0, 9000), None, True), ((0, 0, 9000), 3.0, False)],
)
def test_mock_accelerometer_is_shaken(steami, raw, g, shaken):
    s = board(steami)
    accelerometer = steami["Accelerometer"]()
    set_raw(s, 0x6B, 0x28, *raw)  # 4096 is about 1 g, 9000 about 2.2 g
    assert (accelerometer.is_shaken() if g is None else accelerometer.is_shaken(g)) is shaken


def test_mock_accelerometer_shaken_is_a_strict_comparison(steami):
    s = board(steami)
    accelerometer = steami["Accelerometer"]()
    set_raw(s, 0x6B, 0x28, 0, 0, 4096)
    assert accelerometer.is_shaken(accelerometer.strength()) is False


def test_mock_accelerometer_absent(steami):
    s = board(steami, missing=("ISM330DL",))
    accelerometer = steami["Accelerometer"]()
    assert nan_vector(accelerometer.read())
    assert math.isnan(accelerometer.x())
    assert math.isnan(accelerometer.strength())
    assert accelerometer.is_shaken() is False
    assert s.messages() == [
        "[STeaMi] Accelerometer: the ISM330DL accelerometer (I2C 0x6B) did not answer. "
        + HINT
        + " (E10)"
    ]


def test_mock_accelerometer_failed_read(steami):
    s = board(steami)
    accelerometer = steami["Accelerometer"]()
    assert accelerometer.begin() is True
    del s.bus._devices[0x6B]
    assert nan_vector(accelerometer.read())
    assert accelerometer.is_shaken() is False


def test_mock_gyroscope_reads_dps(steami):
    s = board(steami)
    gyroscope = steami["Gyroscope"]()
    set_raw(s, 0x6B, 0x22, 1000, -2000, 3000)
    expected_dps = s.steami.ism330dl().gyroscope_dps()
    vector = gyroscope.read()
    assert vector == pytest.approx(expected_dps)
    assert vector.x > 0 > vector.y
    assert (gyroscope.x(), gyroscope.y(), gyroscope.z()) == pytest.approx(expected_dps)
    assert s.messages() == []


def test_mock_gyroscope_absent(steami):
    s = board(steami, missing=("ISM330DL",))
    gyroscope = steami["Gyroscope"]()
    assert nan_vector(gyroscope.read())
    assert math.isnan(gyroscope.z())
    assert s.messages() == [
        "[STeaMi] Gyroscope: the ISM330DL gyroscope (I2C 0x6B) did not answer. " + HINT + " (E10)"
    ]


def test_mock_gyroscope_failed_read(steami):
    s = board(steami)
    gyroscope = steami["Gyroscope"]()
    assert gyroscope.begin() is True
    del s.bus._devices[0x6B]
    assert nan_vector(gyroscope.read())


def test_mock_magnetometer_reads_microtesla(steami):
    s = board(steami)
    magnetometer = steami["Magnetometer"]()
    set_field(s, 300, -150, 450)
    vector = magnetometer.read()
    assert vector == pytest.approx((45.0, -22.5, 67.5))  # 0.15 uT/LSB
    assert (magnetometer.x(), magnetometer.y(), magnetometer.z()) == pytest.approx(
        (45.0, -22.5, 67.5)
    )
    assert magnetometer.strength() == pytest.approx(math.sqrt(45.0**2 + 22.5**2 + 67.5**2))
    assert magnetometer.chip() == "LIS2MDL"
    assert s.messages() == []


def test_mock_magnetometer_subtracts_the_offset_in_lsb(steami):
    s = board(steami)
    magnetometer = steami["Magnetometer"]()
    set_field(s, 300, -150, 450)
    mag = s.steami.lis2mdl()
    mag.x_off, mag.y_off, mag.z_off = 100, -50, 50
    assert magnetometer.read() == pytest.approx((30.0, -15.0, 60.0))


def test_mock_magnetometer_uses_the_config_zone_calibration(steami):
    config = '{"rev": 131, "cm": {"hx": 100, "hy": -50, "hz": 50, "sx": 1, "sy": 1, "sz": 1}}'
    s = board(steami, config=config, zone=True)
    magnetometer = steami["Magnetometer"]()
    set_field(s, 300, -150, 450)
    assert magnetometer.read() == pytest.approx((30.0, -15.0, 60.0))
    assert s.steami.calibrated("LIS2MDL") is True


def test_mock_magnetometer_absent(steami):
    s = board(steami, missing=("LIS2MDL",))
    magnetometer = steami["Magnetometer"]()
    assert nan_vector(magnetometer.read())
    assert math.isnan(magnetometer.strength())
    magnetometer.calibrate(1)  # nothing to calibrate, no error
    assert s.messages() == [
        "[STeaMi] Magnetometer: the LIS2MDL magnetometer (I2C 0x1E) did not answer. "
        + HINT
        + " (E10)"
    ]


def test_mock_magnetometer_failed_read(steami):
    s = board(steami)
    magnetometer = steami["Magnetometer"]()
    assert magnetometer.begin() is True
    del s.bus._devices[0x1E]
    assert nan_vector(magnetometer.read())
    assert math.isnan(magnetometer.strength())


def test_mock_magnetometer_and_compass_share_one_driver(steami):
    s = board(steami)
    magnetometer, compass = steami["Magnetometer"](), steami["Compass"]()
    assert magnetometer.begin() is True
    assert compass.begin() is True
    assert magnetometer._driver() is compass._driver() is s.steami.lis2mdl()


@pytest.fixture
def fake_time(steami):
    """The sleeps of the LIS2MDL driver, recorded instead of waited for."""
    import lis2mdl.device

    sleeps = []
    saved = lis2mdl.device.sleep_ms
    lis2mdl.device.sleep_ms = sleeps.append
    yield sleeps
    lis2mdl.device.sleep_ms = saved


@pytest.mark.parametrize(
    ("x", "y", "heading"),
    [
        (0, 100, 0),
        (-100, 100, 45),
        (-100, 0, 90),
        (-100, -100, 135),
        (0, -100, 180),
        (100, -100, 225),
        (100, 0, 270),
        (100, 100, 315),
    ],
)
def test_mock_compass_heading_of_a_known_field(steami, x, y, heading):
    s = board(steami)
    compass = steami["Compass"]()
    set_field(s, x, y, 300)
    assert compass.heading() == pytest.approx(heading)
    assert s.messages() == []


def test_mock_compass_heading_is_in_0_360(steami):
    s = board(steami)
    compass = steami["Compass"]()
    set_field(s, 300, -150)  # atan2(-300, -150) is negative
    assert compass.heading() == pytest.approx(243.4349, abs=1e-3)


@pytest.mark.parametrize(
    ("heading", "text"),
    [
        (0, "N"),
        (22.4, "N"),
        (22.5, "NE"),
        (45, "NE"),
        (67.5, "E"),
        (90, "E"),
        (112.5, "SE"),
        (157.5, "S"),
        (180, "S"),
        (202.5, "SW"),
        (247.5, "W"),
        (270, "W"),
        (292.5, "NW"),
        (337.4, "NW"),
        (337.5, "N"),
    ],
)
def test_mock_compass_direction_sectors(steami, heading, text):
    s = board(steami)
    compass = steami["Compass"]()
    set_field(s, 0, 100)  # north: the declination moves the heading
    compass.set_declination(heading)
    assert compass.heading() == pytest.approx(heading)
    assert compass.direction() == text


def test_mock_compass_declination_set_before_begin_is_applied_once_started(steami):
    s = board(steami)
    compass = steami["Compass"]()
    set_field(s, 0, 100)
    compass.set_declination(-2.5)
    assert s.bus.get_write_log() == [] and s.reads == []  # still no hardware
    assert compass.heading() == pytest.approx(357.5)
    compass.set_declination(10)  # after begin(): reaches the driver at once
    assert s.steami.lis2mdl()._declination_deg == 10
    assert compass.heading() == pytest.approx(10)


def test_mock_compass_declination_is_shared_with_the_driver_only(steami):
    s = board(steami)
    compass = steami["Compass"]()
    compass.set_declination(3)
    assert compass.begin() is True
    assert s.steami.lis2mdl()._declination_deg == 3


def test_mock_compass_absent(steami):
    s = board(steami, missing=("LIS2MDL",))
    compass = steami["Compass"]()
    assert math.isnan(compass.heading())
    assert compass.direction() == ""
    compass.set_declination(5)
    compass.calibrate(1)
    assert s.messages() == [
        "[STeaMi] Compass: the LIS2MDL compass (I2C 0x1E) did not answer. " + HINT + " (E10)"
    ]


def test_mock_compass_failed_read(steami):
    s = board(steami)
    compass = steami["Compass"]()
    assert compass.begin() is True
    del s.bus._devices[0x1E]
    assert math.isnan(compass.heading())
    assert compass.direction() == ""


def set_accel_g(s, ax, ay, az):
    """The raw acceleration of the ISM330DL at +-8 g (0.244 mg/LSB), from values in g."""
    set_raw(s, 0x6B, 0x28, *(round(v / 0.000244) for v in (ax, ay, az)))


@pytest.mark.parametrize(("x", "y"), [(0, 100), (-100, 100), (-100, 0), (300, -150), (100, 100)])
def test_mock_compass_tilt_heading_flat_is_the_flat_heading(steami, x, y):
    s = board(steami)
    compass = steami["Compass"]()
    set_field(s, x, y, 300)
    set_accel_g(s, 0, 0, -1)  # screen up and flat
    assert compass.heading_tilt_compensated() == compass.heading()
    assert s.messages() == []


def test_mock_compass_tilt_heading_sets_the_accelerometer_range(steami):
    s = board(steami)
    compass = steami["Compass"]()
    set_field(s, 0, 100, 300)
    set_accel_g(s, 0, 0, -1)
    s.bus.clear_write_log()
    assert compass.heading_tilt_compensated() == pytest.approx(0)
    assert (*CTRL1_XL, b"\x4c") in s.bus.get_write_log()  # +-8 g at 104 Hz, as Accelerometer


@pytest.mark.parametrize("sign", [1, -1])
def test_mock_compass_tilt_heading_removes_the_roll_error(steami, sign):
    # Pointing north with the right edge raised by 20 degrees, dip 60 degrees.
    s = board(steami)
    compass = steami["Compass"]()
    driver_sign = s.steami.lis2mdl()._MAG_Z_SIGN
    r = math.radians(20 * sign)
    h, v = 500 * 0.5, 500 * math.sqrt(3) / 2
    field = (-v * math.sin(r), h, driver_sign * -v * math.cos(r))
    set_field(s, *(round(c) for c in field))
    set_accel_g(s, 0, -math.sin(r), -math.cos(r))
    tilt = compass.heading_tilt_compensated()
    assert min(tilt, 360 - tilt) == pytest.approx(0, abs=0.1)
    flat = compass.heading()
    assert min(flat, 360 - flat) > 25  # the flat heading is about 30 degrees off


def test_mock_compass_tilt_heading_without_accelerometer(steami):
    s = board(steami, missing=("ISM330DL",))
    compass = steami["Compass"]()
    set_field(s, 0, 100, 300)
    assert math.isnan(compass.heading_tilt_compensated())
    assert compass.heading() == pytest.approx(0)  # the flat heading does not need it


def test_mock_compass_tilt_heading_without_magnetometer(steami):
    s = board(steami, missing=("LIS2MDL",))
    compass = steami["Compass"]()
    set_accel_g(s, 0, 0, -1)
    assert math.isnan(compass.heading_tilt_compensated())


@pytest.mark.parametrize("address", [0x6B, 0x1E])
def test_mock_compass_tilt_heading_failed_read(steami, address):
    s = board(steami)
    compass = steami["Compass"]()
    set_field(s, 0, 100, 300)
    set_accel_g(s, 0, 0, -1)
    assert compass.heading_tilt_compensated() == pytest.approx(0)
    del s.bus._devices[address]
    assert math.isnan(compass.heading_tilt_compensated())


def test_mock_compass_tilt_heading_without_gravity_is_nan(steami):
    s = board(steami)
    compass = steami["Compass"]()
    set_field(s, 0, 100, 300)
    set_accel_g(s, 0, 0, 0)
    assert math.isnan(compass.heading_tilt_compensated())


@pytest.mark.parametrize("cls", ["Magnetometer", "Compass"])
def test_mock_calibrate_stores_the_result_in_the_driver(steami, fake_time, cls):
    s = board(steami, config='{"rev": 131}', zone=True)
    function = steami[cls]()
    assert function.begin() is True
    mag = s.steami.lis2mdl()
    fields = [(100, 200, 300), (300, 600, 500), (200, 400, 100)]
    calls = []

    def moving_field():
        calls.append(1)
        return fields[len(calls) % 3]

    mag.magnetic_field = moving_field
    s.bus.clear_write_log()
    fake_time.clear()  # the sleeps of the driver start
    function.calibrate(2)
    assert len(calls) == 2 * 50  # 50 samples a second, 20 ms apart
    assert fake_time == [20] * 100
    assert (mag.x_off, mag.y_off, mag.z_off) == (200, 400, 300)
    assert (mag.x_scale, mag.y_scale, mag.z_scale) == (100, 200, 200)
    # Nothing is written to the board: the config zone keeps what it has.
    assert s.bus.get_write_log() == []
    assert s.bridge.config == '{"rev": 131}'


@pytest.mark.parametrize("cls", ["Magnetometer", "Compass"])
def test_mock_calibrate_default_is_12_seconds(steami, fake_time, cls):
    s = board(steami)
    function = steami[cls]()
    set_field(s, 1, 2, 3)
    assert function.begin() is True
    fake_time.clear()
    function.calibrate()
    assert len(fake_time) == 12 * 50


@pytest.mark.parametrize("cls", ["Magnetometer", "Compass"])
def test_mock_calibrate_zero_seconds_changes_nothing(steami, fake_time, cls):
    s = board(steami)
    function = steami[cls]()
    assert function.begin() is True
    mag = s.steami.lis2mdl()
    mag.set_calibrate_step(5, 6, 7, 1.5, 2.5, 3.5)
    fake_time.clear()
    function.calibrate(0)
    assert fake_time == []
    assert (mag.x_off, mag.y_scale) == (5, 2.5)


@pytest.mark.parametrize("cls", ["Magnetometer", "Compass"])
def test_mock_calibrate_caps_the_samples(steami, cls):
    s = board(steami)
    function = steami[cls]()
    assert function.begin() is True
    asked = []
    s.steami.lis2mdl().calibrate_minmax_3d = lambda samples, delay: asked.append((samples, delay))
    function.calibrate(5000)  # 250000 samples would not fit in 16 bits
    assert asked == [(65535, 20)]


def test_mock_compass_heading_uses_the_calibration(steami, fake_time):
    s = board(steami)
    compass = steami["Compass"]()
    set_field(s, -50, 100)
    s.steami.lis2mdl().set_calibrate_step(-50, 0, 0, 1, 1, 1)  # the offset cancels x
    assert compass.heading() == pytest.approx(0)


# --------------------------
# Light, Color and Gesture
# --------------------------

ENABLE = 0x80
AEN, GEN = 1 << 1, 1 << 6  # ambient light and gesture engines in ENABLE


def enable_bits(s):
    return s.bus._devices[0x39][ENABLE][0]


def enable_writes(s):
    return [w for w in s.bus.get_write_log() if w[:2] == (0x39, ENABLE)]


@pytest.fixture
def apds_time(steami):
    """The clock and the sleeps of the gesture function and of the APDS-9960 driver."""
    import apds9960.device
    import steami.gesture

    clock = [0]
    saved = (apds9960.device.sleep_ms, steami.gesture.ticks_ms, steami.gesture.ticks_diff)
    apds9960.device.sleep_ms = lambda ms: None
    steami.gesture.ticks_ms = lambda: clock[0]
    steami.gesture.ticks_diff = lambda a, b: a - b
    yield clock
    apds9960.device.sleep_ms, steami.gesture.ticks_ms, steami.gesture.ticks_diff = saved


def test_mock_light_reads_the_clear_channel(steami):
    s = board(steami, V1AB)
    light = steami["Light"]()
    assert light.read() == 256
    assert light.chip() == "APDS-9960"
    assert s.messages() == []


def test_mock_color_reads_a_tuple_and_each_channel(steami):
    board(steami, V1AB)
    color = steami["Color"]()
    assert color.read() == (128, 64, 32)
    assert isinstance(color.read(), tuple)
    assert (color.red(), color.green(), color.blue()) == (128, 64, 32)


def test_mock_color_rgb_scales_the_largest_channel_to_255(steami):
    board(steami, V1AB)
    color = steami["Color"]()
    # (128, 64, 32): 128 -> 255, the others rounded as Arduino SteamiColor::rgb().
    assert color.rgb() == (255, 128, 64)
    assert isinstance(color.rgb(), tuple)


@pytest.mark.parametrize(
    ("counts", "expected"),
    [
        ((0, 0, 0), (0, 0, 0)),
        ((3, 0, 1), (255, 0, 85)),
        ((7, 2, 1), (255, 73, 36)),
        ((65535, 65535, 1), (255, 255, 0)),
        ((1, 1, 1), (255, 255, 255)),
    ],
)
def test_mock_color_rgb_rounds_as_arduino(steami, counts, expected):
    s = board(steami, V1AB)
    color = steami["Color"]()
    assert color.begin() is True
    driver = s.steami.apds9960()
    driver.red_light = lambda: counts[0]
    driver.green_light = lambda: counts[1]
    driver.blue_light = lambda: counts[2]
    assert color.rgb() == expected


def test_mock_color_rgb_absent_or_failing_is_black(steami):
    board(steami)
    assert steami["Color"]().rgb() == (0, 0, 0)
    s = board(steami, V1AB)
    color = steami["Color"]()
    assert color.begin() is True

    def fail():
        raise OSError("bus")

    s.steami.apds9960().red_light = fail
    assert color.rgb() == (0, 0, 0)


def test_mock_light_color_and_gesture_share_one_driver(steami):
    s = board(steami, V1AB)
    light, color, gesture = steami["Light"](), steami["Color"](), steami["Gesture"]()
    assert light.begin() and color.begin() and gesture.begin()
    assert light._driver() is color._driver() is gesture._driver() is s.steami.apds9960()


def test_mock_light_and_color_do_not_turn_the_gesture_engine_on(steami):
    s = board(steami, V1AB)
    assert steami["Light"]().read() == 256
    assert steami["Color"]().read() == (128, 64, 32)
    assert enable_bits(s) & AEN
    assert not enable_bits(s) & GEN


def test_mock_gesture_begin_enables_its_engine_once_and_keeps_the_light_one(steami):
    s = board(steami, V1AB)
    steami["Light"]().read()
    gesture = steami["Gesture"]()
    s.bus.clear_write_log()
    assert gesture.begin() is True
    assert enable_bits(s) & GEN and enable_bits(s) & AEN
    written = enable_writes(s)
    assert written
    assert gesture.begin() is True
    assert gesture.read() == steami["Gesture"].NONE
    assert enable_writes(s) == written


def test_mock_light_after_gesture_keeps_the_gesture_engine(steami):
    s = board(steami, V1AB)
    assert steami["Gesture"]().begin() is True
    assert steami["Light"]().read() == 256
    assert enable_bits(s) & GEN and enable_bits(s) & AEN


def test_mock_gesture_constants_are_the_arduino_texts(steami):
    gesture_cls = steami["Gesture"]
    assert (
        gesture_cls.NONE,
        gesture_cls.UP,
        gesture_cls.DOWN,
        gesture_cls.LEFT,
        gesture_cls.RIGHT,
    ) == (
        "NONE",
        "UP",
        "DOWN",
        "LEFT",
        "RIGHT",
    )
    assert (gesture_cls.NEAR, gesture_cls.FAR) == ("NEAR", "FAR")
    for text in ("NONE", "LEFT", "RIGHT", "UP", "DOWN", "NEAR", "FAR"):
        assert gesture_cls.name(getattr(gesture_cls, text)) == text
    assert gesture_cls.name("sideways") == "NONE"


def test_mock_gesture_names_follow_the_driver_directions(steami):
    import apds9960.const as c

    s = board(steami, V1AB)
    gesture = steami["Gesture"]()
    driver = s.steami.apds9960()
    expected = {
        c.APDS9960_DIR_NONE: "NONE",
        c.APDS9960_DIR_LEFT: "LEFT",
        c.APDS9960_DIR_RIGHT: "RIGHT",
        c.APDS9960_DIR_UP: "UP",
        c.APDS9960_DIR_DOWN: "DOWN",
        c.APDS9960_DIR_NEAR: "NEAR",
        c.APDS9960_DIR_FAR: "FAR",
    }
    assert gesture.begin() is True
    for direction, text in expected.items():
        driver.gesture = lambda direction=direction: direction
        assert gesture.read() == text


def test_mock_gesture_default_timeout_reads_once(steami, apds_time):
    s = board(steami, V1AB)
    gesture = steami["Gesture"]()
    driver = s.steami.apds9960()
    calls = []

    def noise():
        calls.append(1)
        apds_time[0] += 10
        return 0

    driver.gesture = noise
    driver.is_gesture_available = lambda: True
    assert gesture.read() == "NONE"
    assert len(calls) == 1


def test_mock_gesture_timeout_bounds_the_retries(steami, apds_time):
    s = board(steami, V1AB)
    gesture = steami["Gesture"]()
    driver = s.steami.apds9960()
    calls = []

    def noise():
        calls.append(1)
        apds_time[0] += 10
        return 0

    driver.gesture = noise
    driver.is_gesture_available = lambda: True
    assert gesture.read(50) == "NONE"
    assert len(calls) == 5  # 10, 20, 30, 40, 50 ms: the timeout is reached


def test_mock_gesture_retries_stop_when_the_chip_holds_no_more_data(steami, apds_time):
    s = board(steami, V1AB)
    gesture = steami["Gesture"]()
    driver = s.steami.apds9960()
    calls = []
    driver.gesture = lambda: calls.append(1) or 0
    driver.is_gesture_available = lambda: False
    assert gesture.read(1000) == "NONE"
    assert len(calls) == 1


def test_mock_gesture_retry_finds_the_gesture(steami, apds_time):
    s = board(steami, V1AB)
    gesture = steami["Gesture"]()
    driver = s.steami.apds9960()
    answers = [0, 0, 4]
    driver.gesture = lambda: answers.pop(0)
    driver.is_gesture_available = lambda: True
    assert gesture.read(1000) == "DOWN"


@pytest.mark.parametrize("cls", ["Light", "Color", "Gesture"])
def test_mock_apds_function_is_not_on_a_v1c(steami, cls):
    s = board(steami)
    function = steami[cls]()
    assert function.begin() is False
    assert function.status() == steami["const"].Status.NOT_ON_THIS_BOARD
    assert function.error() == "not on this board"
    assert function.chip() == ""
    fallback = {
        "Light": "read() will return 0.",
        "Color": "read() will return (0, 0, 0).",
        "Gesture": "read() will return NONE.",
    }[cls]
    noun = {"Light": "light", "Color": "colour", "Gesture": "gesture"}[cls]
    assert s.messages() == [
        "[STeaMi] {}: this STeaMi is a V1c, it has no {} sensor (APDS-9960 is on V1a/V1b "
        "only). {} (E20)".format(cls, noun, fallback)
    ]


def test_mock_apds_absence_values_on_a_v1c(steami):
    s = board(steami)
    color = steami["Color"]()
    assert steami["Light"]().read() == 0
    assert color.read() == (0, 0, 0)
    assert (color.red(), color.green(), color.blue()) == (0, 0, 0)
    assert steami["Gesture"]().read(100) == steami["Gesture"].NONE
    assert len(s.messages()) == 3
    assert s.bus.get_write_log() == []


@pytest.mark.parametrize("cls", ["Light", "Color", "Gesture"])
def test_mock_apds_function_absent_on_a_v1ab_gives_e10(steami, cls):
    s = board(steami, V1AB, missing=("APDS-9960",))
    function = steami[cls]()
    assert function.begin() is False
    assert function.error() == "no answer"
    assert s.messages()[0].startswith("[STeaMi] {}: the APDS-9960 ".format(cls))
    assert s.messages()[0].endswith("(E10)")


def test_mock_apds_failed_reads(steami):
    s = board(steami, V1AB)
    light, color, gesture = steami["Light"](), steami["Color"](), steami["Gesture"]()
    assert light.begin() and color.begin() and gesture.begin()
    del s.bus._devices[0x39]
    assert light.read() == 0
    assert color.read() == (0, 0, 0)
    assert gesture.read(100) == "NONE"


def test_mock_color_failing_channel_gives_all_zeros(steami):
    s = board(steami, V1AB)
    color = steami["Color"]()
    assert color.begin() is True

    def fail():
        raise OSError("bus")

    s.steami.apds9960().green_light = fail
    assert color.read() == (0, 0, 0)
    assert color.blue() == 0


# --------------------------------------------------
# Buttons
# --------------------------------------------------


class ButtonsRig:
    """A board, its fake button pins, a model of the MCP23009 and a clock that only moves when told.

    Pressing a button pin runs its IRQ handler, as the edge does on the board.
    ``taken`` names pins whose EXTI line is already used: their ``irq()``
    raises OSError, as the firmware does.
    """

    def __init__(self, steami, monkeypatch, release="V1c", taken=(), **kwargs):
        import steami.buttons as module

        self.pins = {}
        pins = self.pins

        class PinStub(FakePin):
            # Pin("A_BUTTON") is the same object at every call, as on the board.
            def __new__(cls, pin_id, *args, **kwargs):
                return pins.get(pin_id) or super().__new__(cls)

            def __init__(self, pin_id, mode=FakePin.IN, pull=None):
                if pin_id in pins:
                    self.init(mode, pull)
                    return
                super().__init__(pin_id, mode, pull)
                self._value = 1  # pulled up: released
                pins[pin_id] = self

            def irq(self, handler=None, trigger=3, *, hard=False):
                if self._id in taken:
                    raise OSError("IRQ resource already taken by Pin('INT_EXPANDER')")
                super().irq(handler, trigger, hard=hard)

        self.now = 1000
        self.later = []  # (time, action) run by advance()
        monkeypatch.setattr(module, "Pin", PinStub)
        monkeypatch.setattr(module, "ticks_ms", lambda: self.now)
        monkeypatch.setattr(module, "sleep_ms", self.advance)
        self.board = board(steami, release, **kwargs)
        self.chip = None
        self.fail_reads = False
        if "MCP23009E" not in kwargs.get("missing", ()):
            self.chip = FakeMCP23009()
            self._attach(self.chip)
        self.buttons = steami["Buttons"]()

    def _attach(self, chip):
        bus = self.board.bus
        read, write = bus.readfrom_mem, bus.writeto_mem

        def readfrom_mem(addr, reg, nbytes, **kwargs):
            if addr != MCP_ADDR:
                return read(addr, reg, nbytes, **kwargs)
            self.board.reads.append((addr, reg))
            if self.fail_reads:
                raise OSError(5, "bus")
            return chip.readfrom_mem(addr, reg, nbytes, **kwargs)

        def writeto_mem(addr, reg, buf, **kwargs):
            if addr != MCP_ADDR:
                return write(addr, reg, buf, **kwargs)
            self.board.reads.append((addr, "writeto_mem"))
            return chip.writeto_mem(addr, reg, buf, **kwargs)

        bus.readfrom_mem = readfrom_mem
        bus.writeto_mem = writeto_mem

    def advance(self, ms):
        self.now += ms
        for item in [i for i in self.later if i[0] <= self.now]:
            self.later.remove(item)
            item[1]()

    def at(self, delay, action):
        """Run action once the clock has moved delay ms from now."""
        self.later.append((self.now + delay, action))

    def press(self, name):
        self.pins[name + "_BUTTON"].drive(0)

    def release(self, name):
        self.pins[name + "_BUTTON"].drive(1)

    def tap(self, name, ms):
        self.press(name)
        self.advance(ms)
        self.release(name)

    def dpad(self, port):
        """Set the MCP23009 input port (a bit at 0 is a pressed button)."""
        self.chip.pins = port
        self.chip._update()


@pytest.fixture
def rig(steami, monkeypatch):
    return ButtonsRig(steami, monkeypatch)


def test_mock_buttons_creating_touches_no_hardware(rig):
    assert rig.pins == {}
    assert rig.board.reads == []
    assert rig.buttons.status() == "not started"


def test_mock_buttons_begin_sets_the_pins_up_with_pull_ups(rig):
    assert rig.buttons.begin() is True
    assert sorted(rig.pins) == ["A_BUTTON", "B_BUTTON", "MENU_BUTTON"]
    assert all(pin._pull == FakePin.PULL_UP for pin in rig.pins.values())
    assert all(pin._mode == FakePin.IN for pin in rig.pins.values())
    # The four D-pad bits of the MCP23009E are inputs with a pull-up.
    assert rig.chip.regs[GPPU] == 0xF0  # bits 4 to 7
    assert rig.chip.regs[IODIR] & 0xF0 == 0xF0


def test_mock_buttons_press_gives_one_was_pressed(rig):
    assert rig.buttons.is_pressed("A") is False
    rig.press("A")
    rig.advance(30)
    assert rig.buttons.was_pressed("A") is True
    assert rig.buttons.was_pressed("A") is False  # consumed
    assert rig.buttons.is_pressed("A") is True
    assert rig.buttons.was_released("A") is False
    rig.release("A")
    rig.advance(30)
    assert rig.buttons.is_pressed("A") is False
    assert rig.buttons.was_released("A") is True
    assert rig.buttons.was_released("A") is False


def test_mock_buttons_bounces_give_one_press(rig):
    rig.buttons.begin()
    rig.buttons.is_pressed("B")
    rig.press("B")
    assert rig.buttons.was_pressed("B") is True  # taken at once
    for level_low in (False, True, False, True):  # bounces within 20 ms
        rig.advance(4)
        (rig.press if level_low else rig.release)("B")
        assert rig.buttons.is_pressed("B") is True
    assert rig.buttons.was_pressed("B") is False
    assert rig.buttons.was_released("B") is False


def test_mock_buttons_a_short_pulse_is_held_until_20_ms_have_passed(rig):
    rig.buttons.begin()
    rig.buttons.is_pressed("MENU")
    rig.press("MENU")
    assert rig.buttons.is_pressed("MENU") is True
    rig.advance(5)
    rig.release("MENU")
    assert rig.buttons.is_pressed("MENU") is True  # the release is locked out
    rig.advance(14)
    assert rig.buttons.is_pressed("MENU") is True
    rig.advance(1)
    assert rig.buttons.is_pressed("MENU") is False
    assert rig.buttons.was_pressed("MENU") is True
    assert rig.buttons.was_released("MENU") is True


def test_mock_buttons_held_at_start_is_not_a_press(rig):
    rig.buttons.begin()
    rig.press("A")  # held before the first read
    assert rig.buttons.is_pressed("A") is True
    assert rig.buttons.was_pressed("A") is False


def test_mock_buttons_unknown_name_raises(rig):
    for method in (rig.buttons.is_pressed, rig.buttons.was_pressed, rig.buttons.was_released):
        for name in ("X", "a", "", None):
            with pytest.raises(ValueError):
                method(name)


@pytest.mark.parametrize(("name", "bit"), [("UP", 7), ("DOWN", 5), ("LEFT", 6), ("RIGHT", 4)])
def test_mock_buttons_dpad_bits(rig, name, bit):
    rig.buttons.begin()
    rig.dpad(0xFF)
    assert rig.buttons.is_pressed(name) is False
    rig.advance(30)
    rig.dpad(0xFF & ~(1 << bit))
    pressed = [n for n in ("UP", "DOWN", "LEFT", "RIGHT") if rig.buttons.is_pressed(n)]
    assert pressed == [name]
    assert rig.buttons.was_pressed(name) is True


def test_mock_buttons_without_the_expander_the_dpad_stays_released(steami, monkeypatch):
    rig = ButtonsRig(steami, monkeypatch, missing=("MCP23009E",))
    assert rig.buttons.begin() is False
    assert rig.buttons.error() == "no answer"
    assert rig.board.messages()[0] == (
        "[STeaMi] Buttons: the MCP23009E D-PAD expander (I2C 0x20) did not answer. "
        "The A, B and MENU buttons still work. (E10)"
    )
    for name in ("UP", "DOWN", "LEFT", "RIGHT"):
        assert rig.buttons.is_pressed(name) is False
    rig.press("A")
    rig.advance(30)
    assert rig.buttons.is_pressed("A") is True
    assert rig.buttons.was_pressed("A") is True
    rig.at(5, lambda: rig.press("MENU"))  # during the wait
    assert rig.buttons.wait_for_press(20) == "MENU"


def test_mock_buttons_work_without_begin_and_dpad_failures_read_released(rig):
    assert rig.buttons.is_pressed("A") is False  # calls begin() itself
    assert rig.buttons.is_available() is True

    rig.fail_reads = True
    rig.press("B")
    assert rig.buttons.is_pressed("B") is True
    assert rig.buttons.is_pressed("UP") is False


def test_mock_buttons_wait_for_press_returns_the_name(rig):
    rig.buttons.begin()
    rig.press("A")  # held at start: not a press
    rig.buttons.is_pressed("A")
    rig.at(100, lambda: rig.dpad(0xFF & ~(1 << 5)))
    assert rig.buttons.wait_for_press() == "DOWN"
    assert rig.buttons.was_pressed("DOWN") is False  # consumed by the wait


def test_mock_buttons_wait_for_press_drops_presses_latched_before(rig):
    rig.buttons.begin()
    rig.buttons.is_pressed("A")
    rig.press("A")
    rig.advance(30)
    assert rig.buttons.is_pressed("A") is True  # latched a press of A
    assert rig.buttons.wait_for_press(100) is None
    assert rig.buttons.was_pressed("A") is False


def test_mock_buttons_wait_for_press_times_out(rig):
    start = rig.now
    assert rig.buttons.wait_for_press(100) is None
    assert 100 <= rig.now - start < 110


def test_mock_buttons_a_change_after_the_clock_jumped_is_taken(rig, monkeypatch):
    # MicroPython ticks wrap: a stamp older than 2**29 ms must not lock the button.
    import steami.buttons as module

    def ticks_diff(a, b):  # MicroPython semantics: signed, modulo 2**30
        return ((a - b + 2**29) & (2**30 - 1)) - 2**29

    monkeypatch.setattr(module, "ticks_diff", ticks_diff)
    rig.buttons.begin()
    rig.buttons.is_pressed("A")
    rig.press("A")
    assert rig.buttons.was_pressed("A") is True
    rig.advance(30)
    assert rig.buttons.is_pressed("A") is True  # the stamp is forgotten here
    rig.advance(2**29 + 1000)
    rig.release("A")
    assert rig.buttons.is_pressed("A") is False
    assert rig.buttons.was_released("A") is True


# Buttons: taps made between two calls (issue #497, Arduino #251)


def test_mock_buttons_begin_attaches_hard_irqs_on_both_edges_of_a_b_menu(rig):
    assert rig.buttons.begin() is True
    for pin in rig.pins.values():
        handler, trigger, hard = pin._irq
        assert callable(handler)
        assert trigger == FakePin.IRQ_FALLING | FakePin.IRQ_RISING
        assert hard is True
    # MENU (PA0) and INT_EXPANDER (PB0) share EXTI line 0: the line goes to MENU.
    assert "INT_EXPANDER" not in rig.pins


@pytest.mark.parametrize("name", ["A", "B", "MENU"])
def test_mock_buttons_mcu_tap_between_two_calls_is_caught(rig, name):
    assert rig.buttons.was_pressed(name) is False
    rig.advance(150)
    rig.tap(name, 100)  # a 100 ms tap between two calls 300 ms apart
    rig.advance(50)
    assert rig.buttons.is_pressed(name) is False
    assert rig.buttons.was_pressed(name) is True
    assert rig.buttons.was_released(name) is True
    assert rig.buttons.was_pressed(name) is False
    assert rig.buttons.was_released(name) is False


def test_mock_buttons_mcu_bounces_between_two_calls_give_one_press(rig):
    # Each edge of a bounce runs the IRQ: the lock-out keeps one press and one release.
    assert rig.buttons.is_pressed("A") is False
    rig.advance(50)
    for level in (0, 1, 0, 1, 0):
        rig.pins["A_BUTTON"].drive(level)
        rig.advance(1)
    rig.advance(100)
    for level in (1, 0, 1, 0, 1):
        rig.pins["A_BUTTON"].drive(level)
        rig.advance(2)
    rig.advance(200)
    presses = releases = 0
    for _ in range(5):
        presses += rig.buttons.was_pressed("A")
        releases += rig.buttons.was_released("A")
        rig.advance(30)
    assert (presses, releases) == (1, 1)
    assert rig.buttons.is_pressed("A") is False


def test_mock_buttons_mcu_bounce_after_a_release_is_not_a_press(rig):
    assert rig.buttons.is_pressed("B") is False
    rig.advance(50)
    rig.press("B")
    rig.advance(50)
    assert rig.buttons.was_pressed("B") is True
    rig.advance(100)
    rig.release("B")
    rig.advance(2)
    rig.tap("B", 1)  # a bounce 2 ms after the release the IRQ took
    rig.advance(100)
    assert rig.buttons.was_released("B") is True
    assert rig.buttons.was_pressed("B") is False
    assert rig.buttons.is_pressed("B") is False


def test_mock_buttons_two_mcu_taps_between_two_calls_give_one_press(rig):
    # At most one press per button between two calls: a flag, not a counter.
    assert rig.buttons.is_pressed("MENU") is False
    rig.advance(50)
    for _ in range(2):
        rig.tap("MENU", 60)
        rig.advance(60)
    assert rig.buttons.was_pressed("MENU") is True
    assert rig.buttons.was_pressed("MENU") is False
    assert rig.buttons.was_released("MENU") is True
    assert rig.buttons.was_released("MENU") is False


def test_mock_buttons_mcu_release_then_tap_between_two_calls(rig):
    # Held at one call, released and tapped again before the next one: both are reported.
    assert rig.buttons.is_pressed("A") is False
    rig.advance(50)
    rig.press("A")
    rig.advance(50)
    assert rig.buttons.was_pressed("A") is True
    rig.release("A")
    rig.advance(80)
    rig.tap("A", 80)
    rig.advance(80)
    assert rig.buttons.is_pressed("A") is False
    assert rig.buttons.was_released("A") is True
    assert rig.buttons.was_pressed("A") is True


def test_mock_buttons_mcu_tap_shorter_than_the_lock_out(rig):
    # The IRQ takes the press, ignores the release; the next call reads the pin released.
    assert rig.buttons.is_pressed("A") is False
    rig.advance(50)
    rig.tap("A", 10)
    rig.advance(200)
    assert rig.buttons.is_pressed("A") is False
    assert rig.buttons.was_pressed("A") is True
    assert rig.buttons.was_released("A") is True


def test_mock_buttons_mcu_irq_before_the_first_call_is_ignored(rig):
    rig.buttons.begin()
    rig.tap("B", 50)  # before the first sample: not a press
    rig.advance(50)
    assert rig.buttons.was_pressed("B") is False
    assert rig.buttons.was_released("B") is False


def test_mock_buttons_a_taken_exti_line_leaves_the_button_sampled(steami, monkeypatch):
    # MCP23009E(interrupt_pin=Pin("INT_EXPANDER")) took EXTI line 0 before.
    rig = ButtonsRig(steami, monkeypatch, taken=("MENU_BUTTON",))
    assert rig.buttons.begin() is True
    assert rig.pins["MENU_BUTTON"]._irq is None
    assert rig.pins["A_BUTTON"]._irq is not None
    assert rig.buttons.is_pressed("MENU") is False
    rig.press("MENU")
    assert rig.buttons.is_pressed("MENU") is True
    assert rig.buttons.was_pressed("MENU") is True


@pytest.mark.parametrize(
    ("name", "bit"), [("UP", UP), ("DOWN", DOWN), ("LEFT", LEFT), ("RIGHT", RIGHT)]
)
def test_mock_buttons_dpad_tap_between_two_calls_is_caught(rig, name, bit):
    # The expander latch keeps the tap: the next call finds the press, the
    # release comes one call later and is_pressed() stays true until then.
    assert rig.buttons.was_pressed(name) is False
    rig.advance(150)
    rig.chip.press(bit)
    rig.advance(100)
    rig.chip.release(bit)
    rig.advance(50)
    assert rig.buttons.was_pressed(name) is True
    assert rig.buttons.is_pressed(name) is True
    assert rig.buttons.was_released(name) is False
    rig.advance(300)
    assert rig.buttons.is_pressed(name) is False
    assert rig.buttons.was_released(name) is True
    assert rig.buttons.was_pressed(name) is False


def test_mock_buttons_dpad_read_during_a_release_bounce_gives_no_false_press(rig):
    # A call reads the D-pad in the middle of a release bounce and the next one
    # finds the tail of the bounce: no release then false press.
    assert rig.buttons.is_pressed("DOWN") is False
    rig.advance(50)
    rig.chip.press(DOWN)
    rig.advance(30)
    presses = rig.buttons.was_pressed("DOWN")
    rig.advance(100)
    rig.chip.release(DOWN)
    presses += rig.buttons.was_pressed("DOWN")  # read in the bounce
    releases = rig.buttons.was_released("DOWN")
    rig.chip.press(DOWN)  # tail of the bounce
    rig.chip.release(DOWN)
    rig.advance(30)
    for _ in range(4):
        presses += rig.buttons.was_pressed("DOWN")
        releases += rig.buttons.was_released("DOWN")
        rig.advance(30)
    assert (presses, releases) == (1, 1)
    assert rig.buttons.is_pressed("DOWN") is False


def test_mock_buttons_dpad_bus_error_gives_no_false_press(rig):
    # A failed read must not read as 0, every active-low D-pad button pressed.
    assert rig.buttons.is_pressed("UP") is False
    rig.advance(50)
    rig.fail_reads = True
    presses = 0
    for _ in range(5):
        for name in ("UP", "DOWN", "LEFT", "RIGHT"):
            presses += rig.buttons.was_pressed(name)
            presses += rig.buttons.is_pressed(name)
        rig.advance(30)
    assert presses == 0
    rig.fail_reads = False
    rig.chip.press(LEFT)
    rig.advance(30)
    assert rig.buttons.was_pressed("LEFT") is True


def test_mock_buttons_dpad_held_at_start_is_not_a_press(rig):
    rig.chip.press(UP)
    assert rig.buttons.begin() is True
    assert rig.buttons.was_pressed("UP") is False
    assert rig.buttons.is_pressed("UP") is True
    rig.advance(50)
    assert rig.buttons.was_pressed("UP") is False
    rig.chip.release(UP)
    rig.buttons.is_pressed("UP")
    rig.advance(30)
    assert rig.buttons.was_released("UP") is True
    assert rig.buttons.was_pressed("UP") is False


def test_mock_buttons_wait_for_press_drops_taps_made_before_the_call(rig):
    # Taps latched by an IRQ or by the expander before the call are dropped.
    assert rig.buttons.is_pressed("A") is False
    rig.advance(50)
    rig.tap("A", 60)
    rig.advance(60)
    rig.chip.press(LEFT)
    rig.advance(60)
    rig.chip.release(LEFT)
    rig.advance(60)
    assert rig.buttons.wait_for_press(100) is None


def test_mock_buttons_wait_for_press_returns_a_dpad_press_made_during_the_wait(rig):
    assert rig.buttons.is_pressed("RIGHT") is False
    rig.advance(50)
    rig.at(20, lambda: rig.chip.press(RIGHT))
    start = rig.now
    assert rig.buttons.wait_for_press(500) == "RIGHT"
    assert rig.now - start < 500


def test_mock_buttons_wait_for_press_returns_an_mcu_tap_made_during_the_wait(rig):
    assert rig.buttons.is_pressed("B") is False
    rig.advance(50)
    rig.at(20, lambda: rig.tap("B", 1))  # shorter than one turn of the wait
    assert rig.buttons.wait_for_press(500) == "B"


def test_mock_buttons_deliver_the_pad_callbacks_of_the_program(rig, steami):
    # The calls read the expander through interrupt_event(): the pad callbacks still run.
    rig.chip.release(0)
    assert rig.buttons.begin() is True
    assert rig.buttons.is_pressed("A") is False
    expander = rig.board.steami.mcp23009e()
    falls = []
    mcp = pytest.importorskip("mcp23009e.const")
    expander.setup(0, mcp.MCP23009_DIR_INPUT, mcp.MCP23009_PULLUP)
    expander.interrupt_on_falling(0, lambda: falls.append(1))
    rig.chip.press(0)
    rig.advance(30)
    assert rig.buttons.is_pressed("A") is False
    assert falls == [1]
    assert rig.buttons.was_pressed("UP") is False
    expander.disable_interrupt(0)


def test_mock_buttons_called_last_get_the_interrupts(rig, steami):
    # Two objects: the IRQs and the D-pad events go to the one called last.
    outer = rig.buttons
    assert outer.begin() is True
    assert outer.is_pressed("A") is False
    inner = steami["Buttons"]()
    assert inner.begin() is True
    assert inner.is_pressed("A") is False
    assert outer.is_pressed("A") is False
    rig.advance(50)
    rig.tap("A", 60)
    rig.chip.press(UP)
    rig.chip.release(UP)
    rig.advance(60)
    assert outer.was_pressed("A") is True
    assert outer.was_pressed("UP") is True
    assert inner.was_pressed("A") is False


def test_mock_buttons_dpad_level_is_shared_by_every_object(rig, steami):
    # The D-pad level is the hardware one: an event taken while another object
    # is active must still reach the object that is not.
    first = rig.buttons
    assert first.is_pressed("UP") is False
    rig.advance(50)
    rig.chip.press(UP)
    rig.advance(30)
    assert first.is_pressed("UP") is True
    other = steami["Buttons"]()
    assert other.is_pressed("UP") is True
    rig.advance(50)
    rig.chip.release(UP)  # its event goes to the other object
    other.is_pressed("UP")
    rig.advance(30)
    assert other.is_pressed("UP") is False
    rig.advance(500)
    assert first.is_pressed("UP") is False
    assert first.was_released("UP") is True
    assert first.is_pressed("UP") is False


def test_mock_buttons_dpad_press_while_another_object_is_active(rig, steami):
    first = rig.buttons
    assert first.is_pressed("DOWN") is False
    other = steami["Buttons"]()
    assert other.is_pressed("DOWN") is False
    rig.advance(50)
    rig.chip.press(DOWN)  # held, its event goes to the other object
    rig.advance(30)
    assert other.is_pressed("DOWN") is True
    rig.advance(30)
    assert first.is_pressed("DOWN") is True
    assert first.was_pressed("DOWN") is True
    rig.advance(500)
    assert first.is_pressed("DOWN") is True
