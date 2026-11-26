"""Write the release version into lib/steami/steami/version.py.

Usage: python3 scripts/write_firmware_version.py v0.29.0
"""

import re
import sys
from pathlib import Path

VERSION_FILE = Path(__file__).resolve().parent.parent / "lib" / "steami" / "steami" / "version.py"
TAG_PATTERN = re.compile(r"v\d+\.\d+\.\d+")
_ASSIGNMENT = re.compile(r'^VERSION = "([^"]*)"$', re.MULTILINE)

_TEMPLATE = """# Release version of the library, frozen into the firmware.
# "dev" for a local build; the release workflow rewrites it to the tag (vX.Y.Z).
VERSION = "{}"
"""


def write_version(path, tag):
    """Write `tag` (vX.Y.Z) as VERSION in the file at `path`."""
    if not TAG_PATTERN.fullmatch(tag):
        raise ValueError(f"invalid release tag {tag!r}, expected vX.Y.Z")
    Path(path).write_text(_TEMPLATE.format(tag))


def read_version(path):
    """Return the VERSION string defined in the file at `path`."""
    match = _ASSIGNMENT.search(Path(path).read_text())
    if match is None:
        raise ValueError(f"no VERSION assignment in {path}")
    return match.group(1)


def main(argv):
    if len(argv) != 2:
        print(f"usage: {argv[0]} vX.Y.Z", file=sys.stderr)
        return 2
    try:
        write_version(VERSION_FILE, argv[1])
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print(f"{VERSION_FILE}: VERSION = {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
