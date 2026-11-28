"""Run steami_config/examples/calibrate_temperature.py on fake boards."""

import json
import runpy
from pathlib import Path

import pytest

from tests.test_steami_board_mock import FakeBridge, Setup, board_module  # noqa: F401

TOOL = Path(__file__).parent.parent / "lib/steami_config/examples/calibrate_temperature.py"


class WritableBridge(FakeBridge):
    """A config zone that can also be cleared and written, as save() does."""

    def clear_config(self):
        self.config = ""

    def write_config(self, data):
        self.config = data


def run_tool(board_module, release, config, before=None):  # noqa: F811
    s = Setup(board_module, release=release)
    s.bridge = WritableBridge(True, config)
    s.steami._bridge = s.bridge
    if before is not None:
        before(s.steami)
    runpy.run_path(str(TOOL), run_name="__main__")
    return s, json.loads(s.bridge.config)["tc"]


def test_mock_v1c_uses_the_bme280_as_reference(board_module):  # noqa: F811
    s, tc = run_tool(board_module, "V1c", '{"rev": 131}')
    assert sorted(tc) == ["bme", "ism", "mag"]
    assert tc["bme"] == {"g": 1.0, "o": 0.0}
    ref = s.steami.bme280().temperature()
    for name, key in (("lis2mdl", "mag"), ("ism330dl", "ism")):
        driver = getattr(s.steami, name)()
        assert driver._temp_gain == 1.0
        assert driver.temperature() == pytest.approx(ref, abs=0.01), key


def test_mock_v1ab_uses_the_wsen_hids_and_drops_the_hts_key(board_module):  # noqa: F811
    old = '{"rev": 121, "tc": {"hid": {"g": 1.0, "o": 0.0}, "hts": {"g": 1.0, "o": -3.0}}}'

    def drift(steami):
        steami.wsen_pads().set_temp_offset(4.0)  # a stale correction: reset by the tool

    s, tc = run_tool(board_module, "V1a/V1b", old, before=drift)
    assert sorted(tc) == ["hid", "ism", "mag", "pad"]  # never "hts"
    assert tc["hid"] == {"g": 1.0, "o": 0.0}
    ref = s.steami.wsen_hids().temperature()
    assert s.steami.wsen_pads().temperature() == pytest.approx(ref, abs=0.01)
    assert tc["pad"]["o"] == pytest.approx(ref - 25.0, abs=0.01)  # raw fake reading: 25 C
    # steami applies "hid" now, not the stale legacy correction.
    s.steami._calibration_tried = []
    assert s.steami.calibrate(s.const.Chip.WSEN_HIDS) is True
    assert s.steami.wsen_hids()._temp_offset == 0.0


def test_mock_measures_without_a_previous_calibration(board_module):  # noqa: F811
    s = Setup(board_module, release="V1c")
    s.bridge = WritableBridge(True, '{"rev": 131}')
    s.steami._bridge = s.bridge
    s.steami.lis2mdl().set_temp_offset(5.0)  # applied before the tool runs
    runpy.run_path(str(TOOL), run_name="__main__")
    tc = json.loads(s.bridge.config)["tc"]
    lis = s.steami.lis2mdl()
    lis.set_temp_offset(0.0)
    raw = lis.temperature()
    assert raw + tc["mag"]["o"] == pytest.approx(s.steami.bme280().temperature(), abs=0.01)


def test_mock_unknown_release_writes_nothing(board_module):  # noqa: F811
    s = Setup(board_module, release="V1c", missing=("BME280",))
    s.bridge = WritableBridge(False, "")
    s.steami._bridge = s.bridge
    with pytest.raises(SystemExit):
        runpy.run_path(str(TOOL), run_name="__main__")
    assert s.bridge.config == ""
