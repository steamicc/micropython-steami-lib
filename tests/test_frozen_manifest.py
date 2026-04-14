"""Verify each driver under lib/ is declared in the upstream frozen manifest.

Catches silent regressions where a driver is accidentally removed from, or
forgotten in, the STEAM32_WB55RG board manifest in `steamicc/micropython-steami`.
"""

import ast
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import pytest

LIB_DIR = Path(__file__).parent.parent / "lib"

# Keep this branch in sync with MICROPYTHON_BRANCH in env.mk.
MANIFEST_URL = os.environ.get(
    "STEAMI_FIRMWARE_MANIFEST_URL",
    "https://raw.githubusercontent.com/steamicc/micropython-steami/"
    "stm32-steami-rev1d-final/ports/stm32/boards/STEAM32_WB55RG/manifest.py",
)

STEAMI_LIBRARY = "micropython-steami-lib"


def _extract_required_drivers(source):
    """Parse a board manifest and return the set of driver names required
    from `micropython-steami-lib`. Uses the AST so the check is resilient to
    quoting, spacing, and extra keyword arguments."""
    tree = ast.parse(source)
    required = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id != "require":
            continue
        library = None
        for kw in node.keywords:
            if kw.arg == "library" and isinstance(kw.value, ast.Constant):
                library = kw.value.value
        if library != STEAMI_LIBRARY:
            continue
        if node.args and isinstance(node.args[0], ast.Constant):
            name = node.args[0].value
            if isinstance(name, str):
                required.add(name)
    return required


@pytest.fixture(scope="session")
def frozen_drivers():
    """Fetch the upstream manifest once per session and return the set of
    driver names required from micropython-steami-lib."""
    try:
        with urlopen(MANIFEST_URL, timeout=10) as resp:
            content = resp.read().decode("utf-8")
    except HTTPError as exc:
        pytest.fail(
            f"unexpected HTTP {exc.code} while fetching {MANIFEST_URL}: "
            f"{exc.reason}. The branch or path may have moved — update "
            f"MANIFEST_URL in tests/test_frozen_manifest.py."
        )
    except (URLError, TimeoutError, OSError) as exc:
        pytest.skip(f"cannot fetch upstream manifest: {exc}")
    return _extract_required_drivers(content)


def _discover_driver_dirs():
    return sorted(d for d in LIB_DIR.iterdir() if d.is_dir())


_driver_dirs = _discover_driver_dirs()


@pytest.mark.parametrize(
    "driver_dir",
    _driver_dirs,
    ids=[d.name for d in _driver_dirs],
)
def test_driver_is_frozen_in_firmware_mock(driver_dir, frozen_drivers):
    """Each driver under lib/ must be required in the upstream firmware manifest.

    To intentionally ship a driver outside the firmware, add an empty
    `lib/<driver>/.not-frozen` marker (optionally containing a one-line reason).
    """
    not_frozen = driver_dir / ".not-frozen"
    if not_frozen.exists():
        reason = not_frozen.read_text(encoding="utf-8").strip() or "marked .not-frozen"
        pytest.skip(f"{driver_dir.name}: {reason}")

    assert driver_dir.name in frozen_drivers, (
        f"{driver_dir.name} is not required in the frozen manifest "
        f"({MANIFEST_URL}). Add "
        f'require("{driver_dir.name}", library="micropython-steami-lib") '
        f"to the upstream manifest, or add a lib/{driver_dir.name}/.not-frozen "
        f"marker if the driver is intentionally not shipped."
    )
