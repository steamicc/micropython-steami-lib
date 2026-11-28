"""Tell whether a pull request has to build the MicroPython firmware.

Reads the paths changed by the pull request, one per line, on stdin and
prints `build=true` or `build=false`, a line for $GITHUB_OUTPUT.

Usage: git diff --name-only HEAD^1 HEAD | python3 scripts/firmware_build_needed.py
"""

import sys

# Everything the release build (`make micropython-firmware` in release.yml)
# reads from this repository: the frozen drivers and their manifests, the
# build rules, the version script and the workflows that run them.
FIRMWARE_DIRECTORIES = ("lib/",)
FIRMWARE_FILES = frozenset(
    {
        "Makefile",
        "env.mk",
        "scripts/write_firmware_version.py",
        "scripts/firmware_build_needed.py",
        ".github/workflows/firmware.yml",
        ".github/workflows/release.yml",
    }
)


def build_needed(paths):
    """Return True when one of `paths` is an input of the firmware build."""
    for path in paths:
        path = path.strip()
        if path in FIRMWARE_FILES or path.startswith(FIRMWARE_DIRECTORIES):
            return True
    return False


def main():
    print(f"build={'true' if build_needed(sys.stdin) else 'false'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
