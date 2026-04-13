"""Deploy MicroPython firmware to a STeaMi board via DAPLink USB mass-storage.

Detects the STeaMi volume by its label across Linux, macOS, and Windows,
copies the firmware .bin to it, and lets DAPLink auto-reset the target.

Usage:
    python scripts/deploy_usb.py path/to/firmware.bin
"""

import os
import platform
import shutil
import subprocess
import sys

VOLUME_LABEL = "STeaMi"


def find_steami_linux():
    """Find STeaMi mount point on Linux via findmnt.

    Returns the mount path, or ``None`` if the board is not mounted
    or ``findmnt`` is not available.
    """
    try:
        result = subprocess.run(
            ["findmnt", "-n", "-o", "TARGET", "-S", "LABEL=" + VOLUME_LABEL],
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


def find_steami_macos():
    """Find STeaMi mount point on macOS.

    Returns ``/Volumes/STeaMi`` if the board is mounted, or ``None``.
    """
    path = "/Volumes/" + VOLUME_LABEL
    if os.path.isdir(path):
        return path
    return None


def _find_steami_windows_powershell():
    """Find STeaMi drive letter via PowerShell Get-Volume (preferred)."""
    ps_cmd = (
        "Get-Volume | Where-Object FileSystemLabel -eq '"
        + VOLUME_LABEL
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


def _find_steami_windows_wmic():
    """Find STeaMi drive letter via legacy wmic (fallback for older Windows)."""
    try:
        result = subprocess.run(
            [
                "wmic",
                "logicaldisk",
                "where",
                "VolumeName='" + VOLUME_LABEL + "'",
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


def find_steami_windows():
    """Find STeaMi drive letter on Windows.

    Tries PowerShell Get-Volume first (works on all modern Windows),
    falls back to wmic for older systems where PowerShell is unavailable.
    Returns the drive path (e.g. ``E:\\``), or ``None`` if the board is
    not mounted or neither tool is available.
    """
    return _find_steami_windows_powershell() or _find_steami_windows_wmic()


def find_steami():
    """Detect the STeaMi USB volume across platforms.

    Returns the mount path as a string (e.g. ``/media/user/STeaMi``,
    ``/Volumes/STeaMi``, or ``E:\\``) when a volume with label ``STeaMi``
    is found, or ``None`` if the board is not mounted (or the detection
    tool — findmnt, PowerShell, wmic — is not available on the system).

    Exits with an error on unsupported operating systems.
    """
    system = platform.system()
    if system == "Linux":
        return find_steami_linux()
    if system == "Darwin":
        return find_steami_macos()
    if system == "Windows":
        return find_steami_windows()
    print("Error: unsupported OS: " + system, file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) != 2:
        print("Usage: deploy_usb.py <firmware.bin>", file=sys.stderr)
        sys.exit(1)

    firmware = sys.argv[1]
    if not os.path.isfile(firmware):
        print("Error: firmware binary not found: " + firmware, file=sys.stderr)
        print("Run 'make firmware' first.", file=sys.stderr)
        sys.exit(1)

    mount = find_steami()
    if not mount or not os.path.isdir(mount):
        print(
            "Error: STeaMi board not found (no volume with label '"
            + VOLUME_LABEL
            + "').",
            file=sys.stderr,
        )
        print("Check that the board is connected and mounted.", file=sys.stderr)
        if platform.system() == "Windows":
            print(
                "On Windows, this requires PowerShell (Get-Volume) or wmic.",
                file=sys.stderr,
            )
        sys.exit(1)

    print("Copying firmware to " + mount + "...")
    shutil.copy(firmware, mount)

    # Best-effort flush on Unix (no-op on Windows)
    if hasattr(os, "sync"):
        os.sync()

    print("Firmware deployed via USB. Board will reset automatically.")


if __name__ == "__main__":
    main()
