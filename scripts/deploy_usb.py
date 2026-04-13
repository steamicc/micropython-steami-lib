"""Deploy a firmware binary to a STeaMi board via DAPLink USB mass-storage.

Detects the target volume by its label across Linux, macOS, and Windows,
copies the firmware .bin to it, and lets DAPLink auto-reset the target.

The default label is ``STeaMi`` (normal mode, used for MicroPython firmware).
For DAPLink firmware updates, the board must be in maintenance mode (boot
with the RESET button held) and the volume label is ``MAINTENANCE``.

Usage:
    python scripts/deploy_usb.py path/to/firmware.bin
    python scripts/deploy_usb.py --label MAINTENANCE path/to/daplink.bin
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys


def find_volume_linux(label):
    """Find the mount point of a labelled volume on Linux via findmnt.

    Returns the mount path, or ``None`` if the volume is not mounted
    or ``findmnt`` is not available.
    """
    try:
        result = subprocess.run(
            ["findmnt", "-n", "-o", "TARGET", "-S", "LABEL=" + label],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode == 0:
        mount = result.stdout.strip().split("\n")[0]
        return mount or None
    return None


def find_volume_macos(label):
    """Find the mount point of a labelled volume on macOS.

    Returns ``/Volumes/<label>`` if the volume is mounted, or ``None``.
    """
    path = "/Volumes/" + label
    if os.path.isdir(path):
        return path
    return None


def _find_volume_windows_powershell(label):
    """Find a labelled volume drive letter via PowerShell Get-Volume."""
    ps_cmd = (
        "Get-Volume | Where-Object FileSystemLabel -eq '"
        + label
        + "' | Select-Object -First 1 -ExpandProperty DriveLetter"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode == 0:
        letter = result.stdout.strip()
        if letter:
            return letter + ":\\"
    return None


def _find_volume_windows_wmic(label):
    """Find a labelled volume drive letter via legacy wmic (fallback)."""
    try:
        result = subprocess.run(
            [
                "wmic",
                "logicaldisk",
                "where",
                "VolumeName='" + label + "'",
                "get",
                "DeviceID",
                "/value",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            if line.startswith("DeviceID="):
                drive = line.split("=", 1)[1].strip()
                if drive:
                    return drive + "\\"
    return None


def find_volume_windows(label):
    """Find a labelled volume drive letter on Windows.

    Tries PowerShell Get-Volume first (works on all modern Windows),
    falls back to wmic for older systems where PowerShell is unavailable.
    Returns the drive path (e.g. ``E:\\``), or ``None`` if the volume is
    not mounted or neither tool is available.
    """
    return _find_volume_windows_powershell(label) or _find_volume_windows_wmic(label)


def find_volume(label):
    """Detect a USB volume by its filesystem label across platforms.

    Returns the mount path as a string (e.g. ``/media/user/STeaMi``,
    ``/Volumes/STeaMi``, or ``E:\\``) when a volume with the given label
    is found, or ``None`` if the volume is not mounted (or the detection
    tool — findmnt, PowerShell, wmic — is not available on the system).

    Exits with an error on unsupported operating systems.
    """
    system = platform.system()
    if system == "Linux":
        return find_volume_linux(label)
    if system == "Darwin":
        return find_volume_macos(label)
    if system == "Windows":
        return find_volume_windows(label)
    print("Error: unsupported OS: " + system, file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Deploy a firmware binary to a STeaMi board via USB mass-storage.",
    )
    parser.add_argument(
        "firmware",
        help="Path to the firmware .bin file to deploy.",
    )
    parser.add_argument(
        "--label",
        default="STeaMi",
        help=(
            "Filesystem label of the target volume. "
            "Use 'STeaMi' (default) for MicroPython firmware updates "
            "or 'MAINTENANCE' for DAPLink firmware updates "
            "(the board must be powered on with RESET held to enter maintenance mode)."
        ),
    )
    parser.add_argument(
        "--build-target",
        default="micropython-firmware",
        help=(
            "Make target to suggest if the firmware binary is missing "
            "(default: 'micropython-firmware')."
        ),
    )
    args = parser.parse_args()

    if not os.path.isfile(args.firmware):
        print("Error: firmware binary not found: " + args.firmware, file=sys.stderr)
        print("Run 'make " + args.build_target + "' first.", file=sys.stderr)
        sys.exit(1)

    mount = find_volume(args.label)
    if not mount or not os.path.isdir(mount):
        print(
            "Error: no volume with label '" + args.label + "' found.",
            file=sys.stderr,
        )
        if args.label == "MAINTENANCE":
            print(
                "To enter DAPLink maintenance mode, power on the board with the "
                "RESET button held until the MAINTENANCE volume appears.",
                file=sys.stderr,
            )
        else:
            print(
                "Check that the board is connected and mounted.",
                file=sys.stderr,
            )
        if platform.system() == "Windows":
            print(
                "On Windows, this requires PowerShell (Get-Volume) or wmic.",
                file=sys.stderr,
            )
        sys.exit(1)

    print("Copying firmware to " + mount + "...")
    shutil.copy(args.firmware, mount)

    # Best-effort flush on Unix (no-op on Windows)
    if hasattr(os, "sync"):
        os.sync()

    print("Firmware deployed via USB. Board will reset automatically.")


if __name__ == "__main__":
    main()
