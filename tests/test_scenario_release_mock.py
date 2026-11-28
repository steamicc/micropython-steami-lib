"""Tests of the release filtering of the hardware scenarios (tests/runner/release.py)."""

import importlib.util
import re
import sys
from pathlib import Path

import pytest
import yaml

from tests import test_scenarios as runner
from tests.fake_machine import micropython_stub
from tests.runner import release

ROOT = Path(__file__).parent.parent


def _scenario(name):
    with open(runner.SCENARIOS_DIR / f"{name}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _hardware_names(scenario, board):
    """Names of the hardware tests of a scenario that run on this release."""
    return [
        t["name"]
        for t in scenario["tests"]
        if "hardware" in t.get("mode", ["mock", "hardware"])
        and release.skip_reason(scenario, t, board) is None
    ]


class FakeRequest:
    """Stands for the pytest request: only the board_release fixture."""

    def __init__(self, board):
        self.board = board
        self.asked = []

    def getfixturevalue(self, name):
        self.asked.append(name)
        assert name == "board_release"
        return self.board


class FakeBridge:
    """Stands for MpremoteBridge: returns a result or raises."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def run_raw_script(self, script, mount_dir=None):
        self.calls.append((script, mount_dir))
        if self.error is not None:
            raise self.error
        return self.result


# --------------------------------------------------
# Names
# --------------------------------------------------


def test_names_are_those_of_steami_release(monkeypatch):
    # The runner names must stay the values of steami.Release.
    monkeypatch.setitem(sys.modules, "micropython", micropython_stub)
    spec = importlib.util.spec_from_file_location(
        "_steami_const_for_release_test", ROOT / "lib/steami/steami/const.py"
    )
    const = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(const)
    assert (release.V1A, release.V1B, release.V1C) == (
        const.Release.V1A,
        const.Release.V1B,
        const.Release.V1C,
    )
    assert release.V1AB == const.Release.V1AB
    assert release.UNKNOWN == const.Release.UNKNOWN


# --------------------------------------------------
# YAML values
# --------------------------------------------------


def test_parse_releases_absent_means_every_release():
    assert release.parse_releases(None) is None


def test_parse_releases_list_and_single_name():
    assert release.parse_releases(["V1a", "V1b"]) == ("V1a", "V1b")
    assert release.parse_releases("V1c") == ("V1c",)


@pytest.mark.parametrize("value", [[], {}, 3, ["V1d"], ["v1c"], ["V1a/V1b"]])
def test_parse_releases_rejects_bad_values(value):
    with pytest.raises(ValueError, match="releases"):
        release.parse_releases(value)


def test_test_value_replaces_scenario_value():
    scenario = {"name": "s", "releases": ["V1a", "V1b"]}
    assert release.required_releases(scenario, {"name": "t"}) == ("V1a", "V1b")
    assert release.required_releases(scenario, {"name": "t", "releases": ["V1c"]}) == ("V1c",)
    assert release.required_releases({"name": "s"}, {"name": "t"}) is None


def test_bad_value_names_the_test():
    with pytest.raises(ValueError, match="'bad test'"):
        release.required_releases({"name": "s"}, {"name": "bad test", "releases": ["V2"]})


def test_every_scenario_release_value_is_valid():
    for yaml_file in sorted(runner.SCENARIOS_DIR.glob("*.yaml")):
        with open(yaml_file, encoding="utf-8") as f:
            scenario = yaml.safe_load(f)
        for test in scenario.get("tests", []):
            # Raises ValueError on a typo, naming the scenario or the test.
            release.required_releases(scenario, test)


# --------------------------------------------------
# Filtering
# --------------------------------------------------


@pytest.mark.parametrize(
    ("required", "board", "expected"),
    [
        (None, "V1c", True),
        (None, "", True),
        (("V1c",), "V1c", True),
        (("V1c",), "V1b", False),
        (("V1a", "V1b"), "V1a", True),
        (("V1a", "V1b"), "V1c", False),
        # Probing cannot tell V1a from V1b.
        (("V1a", "V1b"), "V1a/V1b", True),
        (("V1b",), "V1a/V1b", True),
        (("V1c",), "V1a/V1b", False),
        # Unknown release: only the tests with no releases run.
        (("V1c",), "", False),
        (("V1a", "V1b", "V1c"), "", False),
    ],
)
def test_applies(required, board, expected):
    assert release.applies(required, board) is expected


def test_skip_reason_names_both_releases():
    scenario = {"name": "s", "releases": ["V1a", "V1b"]}
    assert release.skip_reason(scenario, {"name": "t"}, "V1a/V1b") is None
    assert release.skip_reason(scenario, {"name": "t"}, "V1c") == (
        "needs a STeaMi V1a or V1b, this board is a V1c"
    )


def test_skip_reason_on_unknown_release_tells_how_to_force():
    reason = release.skip_reason({"name": "s"}, {"name": "t", "releases": ["V1c"]}, "")
    assert "release is unknown" in reason
    assert "--release" in reason


# --------------------------------------------------
# Detection
# --------------------------------------------------


@pytest.mark.parametrize("found", ["V1a", "V1b", "V1c", "V1a/V1b"])
def test_detect_release_returns_steami_begin(found, tmp_path):
    bridge = FakeBridge(result=found)
    assert release.detect_release(bridge, tmp_path) == found
    script, mount_dir = bridge.calls[0]
    assert "Steami.begin()" in script
    assert "set_logger(None)" in script
    assert mount_dir == tmp_path


@pytest.mark.parametrize("answer", ["", None, "V2", 3])
def test_detect_release_unexpected_answer_is_unknown(answer, tmp_path):
    assert release.detect_release(FakeBridge(result=answer), tmp_path) == release.UNKNOWN


@pytest.mark.parametrize("error", [RuntimeError("mpremote failed"), OSError("no port")])
def test_detect_release_failure_is_unknown(error, tmp_path):
    assert release.detect_release(FakeBridge(error=error), tmp_path) == release.UNKNOWN


# --------------------------------------------------
# Scenarios
# --------------------------------------------------


def test_i2c_scan_v1c_runs_only_v1c_and_common_tests():
    names = _hardware_names(_scenario("board_i2c_scan"), "V1c")
    assert "I2C bus scan finds expected devices (V1c)" in names
    assert "No unexpected I2C devices (V1c)" in names
    assert "BME280 chip ID (0x76)" in names
    assert "LIS2MDL WHO_AM_I (0x1E)" in names
    assert not any("V1a/V1b" in n for n in names)
    assert not any(chip in n for n in names for chip in ("APDS9960", "WSEN-PADS", "WSEN-HIDS"))


def test_i2c_scan_v1ab_skips_the_bme280():
    names = _hardware_names(_scenario("board_i2c_scan"), "V1a/V1b")
    assert "I2C bus scan finds expected devices (V1a/V1b)" in names
    assert "APDS9960 device ID (0x39)" in names
    assert "BME280 chip ID (0x76)" not in names
    assert not any("(V1c)" in n for n in names)


def test_i2c_scan_v1c_addresses():
    # One address list per release; the V1c has the BME280 and no V1a/V1b sensor.
    tests = {t["name"]: t for t in _scenario("board_i2c_scan")["tests"]}
    v1c = tests["I2C bus scan finds expected devices (V1c)"]["script"]
    v1ab = tests["I2C bus scan finds expected devices (V1a/V1b)"]["script"]
    assert "0x76" in v1c
    assert not any(a in v1c for a in ("0x39", "0x5D", "0x5F"))
    assert all(a in v1ab for a in ("0x39", "0x5D", "0x5F"))
    assert "0x76" not in v1ab


@pytest.mark.parametrize("name", ["apds9960", "wsen_hids", "wsen_pads", "ssd1327"])
def test_v1ab_driver_scenarios_skip_hardware_on_v1c(name):
    scenario = _scenario(name)
    assert _hardware_names(scenario, "V1c") == []
    assert _hardware_names(scenario, "V1a/V1b") != []


def test_steami_config_real_sensor_calibration_skips_on_v1c():
    # It reads the WSEN-HIDS (0x5F), absent on the V1c. The other hardware
    # tests of steami_config only use the bridge.
    scenario = _scenario("steami_config")
    name = "Apply calibration to real sensor"
    assert name not in _hardware_names(scenario, "V1c")
    assert name in _hardware_names(scenario, "V1a/V1b")
    assert "Save and load config on hardware" in _hardware_names(scenario, "V1c")


# Driver modules of the chips that are only on the V1a/V1b.
_V1AB_ONLY_MODULES = re.compile(r"\b(?:from|import)\s+(wsen_hids|wsen_pads|apds9960)\b")


def test_no_v1c_hardware_test_imports_a_v1ab_only_driver():
    found = []
    for yaml_file in sorted(runner.SCENARIOS_DIR.glob("*.yaml")):
        with open(yaml_file, encoding="utf-8") as f:
            scenario = yaml.safe_load(f)
        for test in scenario.get("tests", []):
            if "hardware" not in test.get("mode", ["mock", "hardware"]):
                continue
            if release.skip_reason(scenario, test, "V1c") is not None:
                continue
            code = (scenario.get("hardware_init") or "") + (test.get("script") or "")
            found.extend(
                f"{yaml_file.name}: {test['name']!r} imports {module}"
                for module in _V1AB_ONLY_MODULES.findall(code)
            )
    assert found == []


@pytest.mark.parametrize("name", ["steami_board", "steami_screen_v1c"])
def test_v1c_scenarios_skip_on_v1ab(name):
    scenario = _scenario(name)
    assert _hardware_names(scenario, "V1a/V1b") == []
    assert _hardware_names(scenario, "V1c") != []


# --------------------------------------------------
# Runner
# --------------------------------------------------


def test_runner_skips_a_test_of_another_release():
    scenario = _scenario("board_i2c_scan")
    test = next(t for t in scenario["tests"] if t["name"] == "BME280 chip ID (0x76)")
    request = FakeRequest("V1a/V1b")
    with pytest.raises(pytest.skip.Exception, match="needs a STeaMi V1c, this board is a V1a/V1b"):
        runner.test_scenario(scenario, test, "hardware", "/dev/ttyACM0", request)
    assert request.asked == ["board_release"]


def test_runner_skips_on_unknown_release():
    scenario = _scenario("steami_board")
    request = FakeRequest(release.UNKNOWN)
    with pytest.raises(pytest.skip.Exception, match="--release"):
        runner.test_scenario(scenario, scenario["tests"][0], "hardware", "/dev/ttyACM0", request)


def test_runner_without_port_skips_before_detection():
    scenario = _scenario("steami_board")
    request = FakeRequest("V1c")
    with pytest.raises(pytest.skip.Exception, match="no --port"):
        runner.test_scenario(scenario, scenario["tests"][0], "hardware", None, request)
    assert request.asked == []


def test_runner_mock_tests_ignore_the_release():
    # A mock test of a V1a/V1b-only driver runs without asking for the release.
    scenario = _scenario("apds9960")
    test = next(t for t in scenario["tests"] if "mock" in t.get("mode", ["mock", "hardware"]))
    request = FakeRequest("V1c")
    runner.test_scenario(scenario, test, "mock", None, request)
    assert request.asked == []
