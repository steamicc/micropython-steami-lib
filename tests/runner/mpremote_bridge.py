"""Bridge to execute driver tests on a real board via mpremote."""

import json
import subprocess
from pathlib import Path

# Root of the project
PROJECT_ROOT = Path(__file__).parent.parent.parent


def _i2c_init_code(i2c_config):
    """Generate MicroPython code to initialize I2C from config.

    Supports both pyboard-style (id only) and ESP32-style (id + scl/sda/freq).
    """
    bus_id = i2c_config.get("id", 0)
    if "scl" in i2c_config and "sda" in i2c_config:
        freq = i2c_config.get("freq", 400000)
        return (
            "from machine import I2C, Pin\n"
            f"i2c = I2C({bus_id}, scl=Pin({i2c_config['scl']}), "
            f"sda=Pin({i2c_config['sda']}), freq={freq})"
        )
    return f"from machine import I2C\ni2c = I2C({bus_id})"


class MpremoteBridge:
    """Executes driver methods on a MicroPython board via mpremote.

    Args:
        port: serial port (e.g. /dev/ttyACM0). None for auto-detect.
    """

    def __init__(self, port=None):
        self.port = port

    def _run(self, code, mount_dir=None):
        """Execute MicroPython code on the board and return stdout.

        Args:
            mount_dir: local directory to mount on the board before exec.
        """
        cmd = ["mpremote"]
        if self.port:
            cmd += ["connect", self.port]
        if mount_dir:
            cmd += ["mount", str(mount_dir)]
        cmd += ["exec", code]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        if result.returncode != 0:
            raise RuntimeError(
                f"mpremote failed: {result.stderr.strip()}"
            )
        # mpremote mount adds "Local directory ... is mounted at /remote"
        # to stdout; filter it out and keep only the script output
        lines = [
            line for line in result.stdout.strip().splitlines()
            if not line.startswith("Local directory ")
        ]
        return "\n".join(lines)

    def _driver_dir(self, driver_name):
        """Return the local lib path for a driver."""
        return PROJECT_ROOT / "lib" / driver_name

    def call_method(
        self, driver_name, driver_class, i2c_config, method,
        args=None, i2c_address=None, module_name=None,
        hardware_init=None,
    ):
        """Call a method on a driver instance and return the result."""
        mod = module_name or driver_name
        args_str = ", ".join(repr(a) for a in (args or []))
        i2c_init = _i2c_init_code(i2c_config)
        if hardware_init is not None:
            dev_init = hardware_init + "\n"
        elif i2c_address is not None:
            dev_init = f"dev = {driver_class}(i2c, address={i2c_address!r})\n"
        else:
            dev_init = f"dev = {driver_class}(i2c)\n"
        code = (
            f"import json\n"
            f"{i2c_init}\n"
            f"from {mod}.device import {driver_class}\n"
            f"{dev_init}"
            f"result = dev.{method}({args_str})\n"
            f"print(json.dumps(result))"
        )
        output = self._run(code, mount_dir=self._driver_dir(driver_name))
        return json.loads(output)

    def read_register(self, i2c_config, i2c_address, register, nbytes=1):
        """Read a register directly from the I2C bus."""
        i2c_init = _i2c_init_code(i2c_config)
        code = (
            f"import json\n"
            f"{i2c_init}\n"
            f"data = i2c.readfrom_mem({i2c_address}, {register}, {nbytes})\n"
            f"print(json.dumps(list(data)))"
        )
        output = self._run(code)
        result = json.loads(output)
        if nbytes == 1:
            return result[0]
        return result

    def run_script(
        self, driver_name, driver_class, i2c_config, script,
        module_name=None, hardware_init=None, i2c_address=None,
    ):
        """Run a custom MicroPython script with driver context.

        The script has access to ``i2c`` and ``dev`` variables and must
        set a ``result`` variable.  The method returns the JSON-decoded
        value of ``result``.

        The script must not print anything: any additional output on
        stdout will cause JSON parsing to fail.

        When ``hardware_init`` is provided it takes precedence over
        ``i2c_address`` for device construction.
        """
        mod = module_name or driver_name
        i2c_init = _i2c_init_code(i2c_config)
        if hardware_init is not None:
            dev_init = hardware_init + "\n"
        elif i2c_address is not None:
            dev_init = f"dev = {driver_class}(i2c, address={i2c_address!r})\n"
        else:
            dev_init = f"dev = {driver_class}(i2c)\n"
        code = (
            f"import json\n"
            f"{i2c_init}\n"
            f"from {mod}.device import {driver_class}\n"
            f"{dev_init}"
            f"{script}\n"
            f"print(json.dumps(result))"
        )
        output = self._run(code, mount_dir=self._driver_dir(driver_name))
        # Parse only the last non-empty line as JSON to ignore stray output
        last_line = output.strip().rsplit("\n", 1)[-1]
        return json.loads(last_line)

    def scan_bus(self, i2c_config):
        """Scan I2C bus and return list of addresses."""
        i2c_init = _i2c_init_code(i2c_config)
        code = (
            f"import json\n"
            f"{i2c_init}\n"
            f"print(json.dumps(i2c.scan()))"
        )
        output = self._run(code)
        return json.loads(output)
