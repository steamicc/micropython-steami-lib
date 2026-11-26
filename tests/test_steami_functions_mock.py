"""Tests of the STeaMi function classes (steami.handle and one module per function)."""

import math

import pytest

from tests.fake_machine import steami_chips
from tests.fake_machine.i2c_bus import FakeI2CBus
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
    from steami.handle import Handle
    from steami.humidity import Humidity
    from steami.pressure import Pressure
    from steami.temperature import Temperature

    yield {
        "board": board_module,
        "const": board_module[1],
        "Handle": Handle,
        "Temperature": Temperature,
        "Humidity": Humidity,
        "Pressure": Pressure,
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
        "[STeaMi] Temperature: this STeaMi is set as a V1c (forced by Steami.begin()), but its "
        "BME280 temperature sensor (I2C 0x76) did not answer. Check Steami.begin() or the board "
        "config. (E11)"
    ]


def test_mock_e11_forced_names_the_first_candidate(steami):
    s = board(steami)
    s.steami.begin("V1a")
    assert steami["Temperature"]().begin() is False
    assert s.messages() == [
        "[STeaMi] Temperature: this STeaMi is set as a V1a (forced by Steami.begin()), but its "
        "WSEN-HIDS temperature sensor (I2C 0x5F) did not answer. Check Steami.begin() or the "
        "board config. (E11)"
    ]


def test_mock_e11_config(steami):
    s = board(steami, V1AB, config='{"rev": 131}', zone=True)
    assert steami["Humidity"]().begin() is False
    assert s.messages() == [
        "[STeaMi] Humidity: this STeaMi is set as a V1c (read from the board config), but its "
        "BME280 humidity sensor (I2C 0x76) did not answer. Check Steami.begin() or the board "
        "config. (E11)"
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
        "[STeaMi] Light: this STeaMi is a V1c, it has no light sensor (APDS-9960 is on V1a/V1b "
        "only). read() will return 0. (E20)"
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
    # The driver raises its own class, which is not an OSError.
    with pytest.raises(WSENHIDSError) as info:
        s.steami.wsen_hids().humidity()
    assert not isinstance(info.value, OSError)
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
