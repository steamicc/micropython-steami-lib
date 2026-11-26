"""Tests of the STeaMi release detection and messages (steami.board)."""

import sys
from pathlib import Path

import pytest

from tests.fake_machine import steami_chips
from tests.runner.executor import cleanup_driver, load_driver_mock

ROOT = Path(__file__).parent.parent


class FakeBridge:
    """Stands for DaplinkBridge: only the config zone calls of detection."""

    def __init__(self, zone=True, config=""):
        self.zone = zone
        self.config = config
        self.read_calls = 0

    def has_config_zone(self):
        return self.zone

    def read_config(self):
        self.read_calls += 1
        return self.config


@pytest.fixture
def board_module():
    """Load steami.board with the fake machine, micropython and time modules."""
    # Reuses the patching of the driver loader (machine, micropython, time).
    load_driver_mock("daplink_bridge", None)
    for name in ("steami_config", "steami"):
        path = str(ROOT / "lib" / name)
        if path not in sys.path:
            sys.path.insert(0, path)
    for mod in list(sys.modules):
        if mod == "steami" or mod.startswith(("steami.", "steami_config")):
            del sys.modules[mod]
    import steami.board
    import steami.const

    steami.board.Steami.end()
    yield steami.board, steami.const
    steami.board.Steami.end()
    cleanup_driver("steami")
    cleanup_driver("daplink_bridge")


class Setup:
    """A board under test: the shared object, its messages and its bus."""

    def __init__(self, board_module, release="V1c", missing=(), config=None, zone=True):
        module, self.const = board_module
        self.steami = module.Steami
        self.bus = steami_chips.board(release, missing=missing)
        self.reads = []
        read = self.bus.readfrom_mem

        def logged_read(addr, reg, nbytes, **kwargs):
            self.reads.append((addr, reg))
            return read(addr, reg, nbytes, **kwargs)

        self.bus.readfrom_mem = logged_read
        self.lines = []
        self.steami.end()
        self.steami._i2c = self.bus
        self.steami.set_logger(self.lines.append)
        self.bridge = None
        if config is not None:
            self.bridge = FakeBridge(zone, config)
            self.steami._bridge = self.bridge


def banner(setup):
    return [line for line in setup.lines if line.startswith("[STeaMi] Board")]


def test_mock_forced(board_module):
    s = Setup(board_module)
    assert s.steami.begin("V1c") == "V1c"
    assert s.steami.release() == "V1c"
    assert s.steami.origin() == s.const.Origin.FORCED
    assert s.reads == []
    assert s.bus.get_write_log() == []
    assert banner(s) == ["[STeaMi] Board V1c (forced by Steami.begin())"]


def test_mock_forced_rejects_unknown_release(board_module):
    s = Setup(board_module)
    with pytest.raises(ValueError):
        s.steami.begin("V2")


def test_mock_config_rev_131(board_module):
    s = Setup(board_module, config='{"rev": 131}')
    assert s.steami.begin() == "V1c"
    assert s.steami.origin() == s.const.Origin.CONFIG
    assert s.steami.revision() == 131
    assert s.steami.is_prototype() is False
    assert banner(s) == ["[STeaMi] Board V1c (read from the board config, revision 131)"]


def test_mock_config_rev_130_prototype(board_module):
    s = Setup(board_module, config='{"rev": 130}')
    assert s.steami.begin() == "V1c"
    assert s.steami.is_prototype() is True
    assert banner(s)[0].endswith(", prototype)")


def test_mock_config_rev_111(board_module):
    s = Setup(board_module, release="V1a/V1b", config='{"rev": 111}')
    assert s.steami.begin() == "V1a"
    assert s.steami.is_v1ab() is True
    assert s.steami.is_v1c() is False


def test_mock_config_rev_121(board_module):
    s = Setup(board_module, release="V1a/V1b", config='{"rev": 121}')
    assert s.steami.begin() == "V1b"
    assert s.steami.is_v1ab() is True


def test_mock_config_invalid_rev(board_module):
    s = Setup(board_module, config='{"rev": 42}')
    assert s.steami.begin() == "V1c"
    assert s.steami.origin() == s.const.Origin.PROBE
    assert s.lines[0] == (
        "[STeaMi] SteamiBoard: unknown board revision 42 in the board config. Update the "
        "STeaMi library; the board is detected from its sensors instead. (E02)"
    )
    assert s.steami.last_error() == s.lines[0]


def test_mock_config_rev_of_another_generation(board_module):
    s = Setup(board_module, config='{"rev": 231}')
    assert s.steami.begin() == "V1c"
    assert s.steami.origin() == s.const.Origin.PROBE
    assert s.lines[0].endswith("(E02)")


def test_mock_config_rev_not_a_number(board_module):
    s = Setup(board_module, config='{"rev": "131"}')
    assert s.steami.begin() == "V1c"
    assert s.steami.origin() == s.const.Origin.PROBE


def test_mock_config_without_rev(board_module):
    s = Setup(board_module, config='{"name": "x"}')
    assert s.steami.begin() == "V1c"
    assert s.steami.origin() == s.const.Origin.PROBE
    assert not any("(E" in line for line in s.lines)


def test_mock_config_bad_json(board_module):
    s = Setup(board_module, config="{not json")
    assert s.steami.begin() == "V1c"
    assert s.steami.origin() == s.const.Origin.PROBE


def test_mock_config_not_an_object(board_module):
    s = Setup(board_module, config="[1, 2]")
    assert s.steami.begin() == "V1c"
    assert s.steami.origin() == s.const.Origin.PROBE


def test_mock_config_empty(board_module):
    s = Setup(board_module, config="")
    assert s.steami.begin() == "V1c"
    assert s.steami.origin() == s.const.Origin.PROBE
    assert s.steami.config() is not None


def test_mock_no_config_zone(board_module):
    s = Setup(board_module, config='{"rev": 131}', zone=False)
    assert s.steami.begin() == "V1c"
    assert s.steami.origin() == s.const.Origin.PROBE
    assert s.bridge.read_calls == 0
    assert s.steami.config() is None


def test_mock_no_bridge(board_module):
    s = Setup(board_module, missing=("DAPLINK",))
    assert s.steami._bridge is None
    assert s.steami.begin() == "V1c"
    assert s.steami.origin() == s.const.Origin.PROBE


def test_mock_probe_v1c(board_module):
    s = Setup(board_module, config="", zone=False)
    assert s.steami.begin() == "V1c"
    assert s.steami.is_v1c() is True
    assert s.steami.revision() is None
    assert s.steami.is_prototype() is False
    assert banner(s) == ["[STeaMi] Board V1c (detected: BME280 at 0x76)"]


def test_mock_probe_v1ab(board_module):
    s = Setup(board_module, release="V1a/V1b", config="", zone=False)
    assert s.steami.begin() == "V1a/V1b"
    assert s.steami.release_name() == "V1a/V1b"
    assert s.steami.is_v1ab() is True
    assert s.steami.is_v1c() is False
    assert banner(s) == ["[STeaMi] Board V1a/V1b (detected: WSEN-HIDS at 0x5F)"]


def test_mock_probe_v1ab_apds9960_only(board_module):
    s = Setup(
        board_module,
        release="V1a/V1b",
        missing=("WSEN-HIDS", "WSEN-PADS"),
        config="",
        zone=False,
    )
    assert s.steami.begin() == "V1a/V1b"
    assert banner(s) == ["[STeaMi] Board V1a/V1b (detected: APDS-9960 at 0x39)"]


def test_mock_unknown(board_module):
    s = Setup(board_module, missing=("BME280",), config="", zone=False)
    assert s.steami.begin() == s.const.Release.UNKNOWN
    assert s.steami.origin() == s.const.Origin.NONE
    assert s.steami.release_name() == "unknown"
    assert banner(s) == ["[STeaMi] Board unknown (nothing detected)"]
    assert sum(line.endswith("(E01)") for line in s.lines) == 1
    assert s.steami.begin() == s.const.Release.UNKNOWN
    assert sum(line.endswith("(E01)") for line in s.lines) == 1
    assert len(banner(s)) == 1


def test_mock_unknown_message(board_module):
    s = Setup(board_module, missing=("BME280",), config="", zone=False)
    s.steami.begin()
    assert s.steami.last_error() == (
        "[STeaMi] SteamiBoard: cannot tell which STeaMi this is: no V1a/V1b or V1c sensor "
        'answered. Call Steami.begin("V1c") (or "V1b", "V1a") at the start of the program. (E01)'
    )


def test_mock_begin_once(board_module):
    s = Setup(board_module)
    assert s.steami.begin() == "V1c"
    assert s.steami.begin("V1a") == "V1c"
    assert s.steami.release() == "V1c"
    assert s.steami.origin() == s.const.Origin.PROBE
    assert len(banner(s)) == 1


def test_mock_release_detects_on_first_use(board_module):
    s = Setup(board_module)
    assert s.steami.release() == "V1c"
    assert s.steami.is_v1c() is True


def test_mock_report_once_per_who_and_code(board_module):
    s = Setup(board_module)
    s.steami.report("Temperature", "E20", "not on this board")
    s.steami.report("Temperature", "E20", "not on this board")
    s.steami.report("Humidity", "E20", "not on this board")
    s.steami.report("Temperature", "E10", "not answering")
    assert s.lines == [
        "[STeaMi] Temperature: not on this board (E20)",
        "[STeaMi] Humidity: not on this board (E20)",
        "[STeaMi] Temperature: not answering (E10)",
    ]


def test_mock_logger_none(board_module, capsys):
    s = Setup(board_module, missing=("BME280",), config="", zone=False)
    s.steami.set_logger(None)
    s.steami.begin()
    assert capsys.readouterr().out == ""
    assert s.lines == []
    assert s.steami.last_error().endswith("(E01)")


def test_mock_default_logger_prints(board_module, capsys):
    s = Setup(board_module)
    s.steami.end()
    s.steami._i2c = s.bus
    s.steami.begin("V1c")
    assert capsys.readouterr().out == "[STeaMi] Board V1c (forced by Steami.begin())\n"


def test_mock_end_forgets_everything(board_module):
    s = Setup(board_module, missing=("BME280",), config="", zone=False)
    s.steami.begin()
    s.steami.end()
    assert s.steami._i2c is None
    assert s.steami._bridge is None
    assert s.steami.last_error() == ""
    s.steami._i2c = steami_chips.board("V1c")
    s.steami.set_logger(s.lines.append)
    s.steami._bridge = FakeBridge(False)
    assert s.steami.begin() == "V1c"
    assert sum(line.endswith("(E01)") for line in s.lines) == 1


def test_mock_i2c_is_created_on_first_call(board_module):
    s = Setup(board_module)
    s.steami.end()
    bus = s.steami.i2c()
    assert s.steami.i2c() is bus


def test_mock_decode_revision(board_module):
    decode = board_module[1].decode_revision
    assert decode(131) == ("V1c", False)
    assert decode(130) == ("V1c", True)
    assert decode(111) == ("V1a", False)
    assert decode(121) == ("V1b", False)
    assert decode(99) is None
    assert decode(1000) is None
    assert decode(141) is None
    assert decode(101) is None
    assert decode(231) is None
    assert decode(None) is None
    assert decode("131") is None
