"""Board release of the hardware scenarios.

A scenario, or one of its tests, may list the STeaMi releases it applies to:

    releases: [V1c]          # or [V1a, V1b]

The value on a test replaces the one of its scenario. A hardware test whose
list does not contain the release of the board is skipped. Mock tests do not
use the board and are never filtered.

The release is found on the board by ``Steami.begin()`` of lib/steami (board
config first, then probing), so the runner has no detection rule of its own.
The names are the values of ``steami.Release``.
"""

import subprocess

# Values of steami.Release (lib/steami/steami/const.py). The release tests
# check that they stay the same.
V1A = "V1a"
V1B = "V1b"
V1C = "V1c"
V1AB = "V1a/V1b"  # probing cannot tell V1a from V1b
UNKNOWN = ""

RELEASES = (V1A, V1B, V1C)

# Runs on the board with lib/ mounted at /remote. Every driver folder goes on
# sys.path, as in steami_board.yaml, so that the lib/ copy of steami is used
# instead of a frozen one. The logger is off: only the result is printed.
DETECT_SCRIPT = """\
import os, sys
for d in os.listdir('/remote'):
    sys.path.insert(0, '/remote/' + d)
from steami import Steami
Steami.set_logger(None)
result = Steami.begin()
"""


def parse_releases(value, where="releases"):
    """Return the releases of a YAML ``releases`` value as a tuple, or None.

    None (field absent) means every release. A single name is accepted in
    place of a list. Raise ValueError on an empty list or an unknown name.
    """
    if value is None:
        return None
    names = [value] if isinstance(value, str) else value
    if not isinstance(names, list) or not names:
        raise ValueError(f"{where}: expected a non-empty list of {', '.join(RELEASES)}")
    for name in names:
        if name not in RELEASES:
            raise ValueError(
                f"{where}: unknown release {name!r}, expected one of {', '.join(RELEASES)}"
            )
    return tuple(names)


def required_releases(scenario, test):
    """Return the releases a test applies to (test value first), or None."""
    if "releases" in test:
        return parse_releases(test["releases"], f"test {test.get('name')!r}")
    name = scenario.get("name", scenario.get("driver"))
    return parse_releases(scenario.get("releases"), f"scenario {name!r}")


def applies(required, release):
    """Return True when a test with these releases runs on this release.

    A V1a/V1b found by probing runs the tests of V1a or of V1b. An unknown
    release runs only the tests with no releases.
    """
    if required is None:
        return True
    if release == V1AB:
        return V1A in required or V1B in required
    return release in required


def skip_reason(scenario, test, release):
    """Return why a hardware test is skipped on this release, or None."""
    required = required_releases(scenario, test)
    if applies(required, release):
        return None
    wanted = " or ".join(required)
    if release == UNKNOWN:
        return (
            f"needs a STeaMi {wanted}, but the board release is unknown "
            "(pass --release V1a, V1b or V1c)"
        )
    return f"needs a STeaMi {wanted}, this board is a {release}"


def detect_release(bridge, lib_dir):
    """Return the release found by Steami.begin() on the board.

    ``bridge`` is an MpremoteBridge; ``lib_dir`` is the local lib/ folder,
    mounted on the board. Return UNKNOWN when the board does not run the
    script or gives an unexpected answer.
    """
    try:
        release = bridge.run_raw_script(DETECT_SCRIPT, mount_dir=lib_dir)
    except (RuntimeError, OSError, subprocess.SubprocessError):
        return UNKNOWN
    if release in (*RELEASES, V1AB):
        return release
    return UNKNOWN
