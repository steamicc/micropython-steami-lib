"""Mock tests of the generated Spleen font module of steami_screen.

spleen.py is generated (never hand-edited): these tests pin the file
itself and the contract the font helpers rely on.
"""

import hashlib
import importlib
from pathlib import Path

import pytest

from tests.runner.executor import cleanup_driver, load_driver_mock

ROOT = Path(__file__).parent.parent
SPLEEN_PATH = ROOT / "lib" / "steami_screen" / "steami_screen" / "spleen.py"
SPLEEN_SHA256 = "c550418ca14a68ca0cb18bdbce2e3eeafb544830d77ce41c601df8a00303ae30"


@pytest.fixture
def sp():
    """The steami_screen.spleen module, imported on CPython."""
    load_driver_mock("steami_screen", None)
    yield importlib.import_module("steami_screen.spleen")
    cleanup_driver("steami_screen")


def test_mock_spleen_is_the_generated_file():
    data = SPLEEN_PATH.read_bytes()
    assert hashlib.sha256(data).hexdigest() == SPLEEN_SHA256
    assert data.split(b"\n", 1)[0] == b"# SPDX-License-Identifier: BSD-2-Clause"


def test_mock_spleen_contract(sp):
    assert sp.VERSION == "2.1.0"
    assert sp.VALUE_KEY == " +-.:0123456789"
    assert len(sp.EXTRA) == len(sp.FOLD) == 33
    assert sp.FOLD[0] == "°"
    assert sp.FOLD[32] == "Y"
    assert sp.F6X12[:4] == (6, 12, 9, None)
    assert sp.F8X16[:4] == (8, 16, 12, None)
    assert sp.F12X24[:4] == (12, 24, 19, sp.VALUE_KEY)
    assert sp.F16X32[:4] == (16, 32, 26, sp.VALUE_KEY)
    faces = (sp.F6X12, sp.F8X16, sp.F12X24, sp.F16X32)
    assert [len(f[4]) for f in faces] == [1536, 2048, 720, 960]
    for face in faces:
        assert isinstance(face[4], bytes)
