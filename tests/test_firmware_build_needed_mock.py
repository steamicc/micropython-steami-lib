"""Tests for the decision of the pull request firmware build."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
SCRIPT = REPO / "scripts" / "firmware_build_needed.py"

_spec = importlib.util.spec_from_file_location("firmware_build_needed", SCRIPT)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
build_needed = _module.build_needed


@pytest.mark.parametrize(
    "path",
    [
        "lib/steami/steami/buttons.py",
        "lib/bme280/manifest.py",
        "lib/im34dt05/.not-frozen",
        "Makefile",
        "env.mk",
        "scripts/write_firmware_version.py",
        "scripts/firmware_build_needed.py",
        ".github/workflows/firmware.yml",
        ".github/workflows/release.yml",
    ],
)
def test_firmware_inputs_need_a_build(path):
    assert build_needed([path])


@pytest.mark.parametrize(
    "path",
    [
        "README.md",
        "CHANGELOG.md",
        "docs/superpowers/plans/plan.md",
        "tests/test_scenarios.py",
        "scripts/deploy_usb.py",
        ".github/workflows/tests.yml",
        "library/steami.py",
        "Makefile.bak",
    ],
)
def test_other_files_do_not_need_a_build(path):
    assert not build_needed([path])


def test_one_firmware_input_among_others_needs_a_build():
    assert build_needed(["README.md", "tests/test_scenarios.py", "lib/gc9a01/gc9a01/device.py"])


def test_no_changed_file_needs_no_build():
    assert not build_needed([])


def test_blank_lines_are_ignored():
    assert not build_needed(["", "  ", "README.md"])


def _run(stdin):
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=stdin,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_main_prints_a_github_output_line_for_a_driver_change():
    assert _run("README.md\nlib/steami/steami/buzzer.py\n").splitlines() == ["build=true"]


def test_main_prints_a_github_output_line_for_a_docs_change():
    assert _run("README.md\ndocs/guide.md\n").splitlines() == ["build=false"]
