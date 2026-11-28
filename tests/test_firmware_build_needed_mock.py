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
    assert _run("README.md\0lib/steami/steami/buzzer.py\0").splitlines() == ["build=true"]


def test_main_prints_a_github_output_line_for_a_docs_change():
    assert _run("README.md\0docs/guide.md\0").splitlines() == ["build=false"]


def _git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


def _decision_after(tmp_path, setup):
    """Commit a base, apply `setup`, commit it, and run the workflow's pipeline."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "ci@example.org")
    _git(tmp_path, "config", "user.name", "ci")
    (tmp_path / "lib" / "bme280").mkdir(parents=True)
    (tmp_path / "lib" / "bme280" / "manifest.py").write_text("freeze('.')\n" * 20)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("guide\n" * 20)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base")
    setup(tmp_path)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "change")
    # Same command as the "decide" step of firmware.yml.
    diff = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", "-z", "HEAD^1", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    ).stdout
    return _run(diff.decode()).strip()


def test_workflow_lists_paths_without_rename_detection():
    workflow = (REPO / ".github" / "workflows" / "firmware.yml").read_text()
    assert "git diff --name-only --no-renames -z HEAD^1 HEAD" in workflow


def test_rename_out_of_lib_needs_a_build(tmp_path):
    def move(repo):
        (repo / "archive").mkdir()
        _git(repo, "mv", "lib/bme280", "archive/bme280")

    assert _decision_after(tmp_path, move) == "build=true"


def test_rename_into_lib_needs_a_build(tmp_path):
    def move(repo):
        _git(repo, "mv", "docs/guide.md", "lib/bme280/guide.md")

    assert _decision_after(tmp_path, move) == "build=true"


def test_rename_between_docs_does_not_need_a_build(tmp_path):
    def move(repo):
        _git(repo, "mv", "docs/guide.md", "docs/manual.md")

    assert _decision_after(tmp_path, move) == "build=false"
