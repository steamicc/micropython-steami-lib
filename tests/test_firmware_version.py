"""Tests for the firmware version written at release time."""

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent

_spec = importlib.util.spec_from_file_location(
    "write_firmware_version", REPO / "scripts" / "write_firmware_version.py"
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
write_version = _module.write_version
read_version = _module.read_version


def test_version_defaults_to_dev():
    assert read_version(REPO / "lib/steami/steami/version.py") == "dev"


def test_write_version_sets_release_tag(tmp_path):
    target = tmp_path / "version.py"
    write_version(target, "v0.29.0")
    assert read_version(target) == "v0.29.0"


def test_write_version_rejects_bad_tag(tmp_path):
    with pytest.raises(ValueError):
        write_version(tmp_path / "version.py", "0.29.0")


def test_rejected_tag_leaves_file_untouched(tmp_path):
    target = tmp_path / "version.py"
    write_version(target, "v1.2.3")
    with pytest.raises(ValueError):
        write_version(target, "v1.2")
    assert read_version(target) == "v1.2.3"
