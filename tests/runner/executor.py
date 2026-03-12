"""Executes test scenarios loaded from YAML files."""

import importlib
import sys
from pathlib import Path


def load_driver_mock(driver_name, fake_i2c, module_name=None):
    """Load a driver using FakeI2C on CPython.

    Patches machine and micropython modules, imports the driver,
    and returns an instance configured with the fake I2C bus.

    Args:
        driver_name: directory name under lib/ (e.g. 'wsen-pads')
        fake_i2c: FakeI2C instance with pre-loaded registers
        module_name: Python module name if different from driver_name
                     (e.g. 'wsen_pads' when dir is 'wsen-pads')
    """
    if module_name is None:
        module_name = driver_name
    from tests.fake_machine import FakeI2C, FakePin
    from tests.fake_machine import micropython_stub

    # Patch modules before importing driver
    import types

    fake_machine = types.ModuleType("machine")
    fake_machine.I2C = FakeI2C
    fake_machine.Pin = FakePin
    fake_machine.lightsleep = lambda ms=0: None

    sys.modules["machine"] = fake_machine
    sys.modules["micropython"] = micropython_stub

    # Patch time module to add MicroPython-specific functions
    import time

    # Use a monotonic clock to emulate MicroPython's ticks_* semantics
    monotonic = getattr(time, "monotonic", time.perf_counter)

    if not hasattr(time, "sleep_ms"):
        time.sleep_ms = lambda ms: time.sleep(ms / 1000)
    if not hasattr(time, "sleep_us"):
        time.sleep_us = lambda us: time.sleep(us / 1000000)
    if not hasattr(time, "ticks_ms"):
        time.ticks_ms = lambda: int(monotonic() * 1000)
    if not hasattr(time, "ticks_us"):
        time.ticks_us = lambda: int(monotonic() * 1000000)
    if not hasattr(time, "ticks_diff"):
        time.ticks_diff = lambda a, b: a - b

    # Create utime module as alias for time (MicroPython compatibility)
    if "utime" not in sys.modules:
        utime = types.ModuleType("utime")
        utime.sleep_ms = time.sleep_ms
        utime.sleep_us = time.sleep_us
        utime.sleep = time.sleep
        utime.ticks_ms = time.ticks_ms
        utime.ticks_us = time.ticks_us
        utime.ticks_diff = time.ticks_diff
        sys.modules["utime"] = utime

    # Add driver lib path to sys.path
    root = Path(__file__).parent.parent.parent
    driver_lib = root / "lib" / driver_name
    if str(driver_lib) not in sys.path:
        sys.path.insert(0, str(driver_lib))

    # Force reimport of the driver module
    for mod_name in list(sys.modules):
        if mod_name.startswith(module_name):
            del sys.modules[mod_name]

    driver_module = importlib.import_module(f"{module_name}.device")
    return driver_module, fake_i2c


def cleanup_driver(driver_name, module_name=None):
    """Remove patched modules after test."""
    mod_prefix = module_name or driver_name
    for mod_name in list(sys.modules):
        if mod_name.startswith(mod_prefix):
            del sys.modules[mod_name]
    sys.modules.pop("machine", None)
    sys.modules.pop("micropython", None)


def run_action(action, driver_instance):
    """Run a single test action against a driver instance.

    Returns the result value from the action.
    """
    action_type = action["action"]

    if action_type == "call":
        method_name = action["method"]
        args = action.get("args", [])
        method = getattr(driver_instance, method_name)
        return method(*args)

    if action_type == "read_register":
        reg = action["register"]
        return driver_instance.i2c.readfrom_mem(
            driver_instance.address, reg, 1
        )[0]

    if action_type == "manual":
        prompt = action.get("prompt", "Manual check required")
        response = input(f"\n  [MANUAL] {prompt} [y/n] ")
        return response.strip().lower() == "y"

    raise ValueError(f"Unknown action type: {action_type}")


def check_result(result, test):
    """Validate a test result against expected values.

    Returns (passed: bool, message: str).
    """
    if "expect" in test:
        expected = test["expect"]
        if result == expected:
            return True, f"got {result!r}"
        return False, f"expected {expected!r}, got {result!r}"

    if "expect_range" in test:
        low, high = test["expect_range"]
        if low <= result <= high:
            return True, f"got {result} (in [{low}, {high}])"
        return False, f"got {result} (out of range [{low}, {high}])"

    if "expect_true" in test:
        if result:
            return True, "OK"
        return False, "expected True, got False"

    if "expect_not_none" in test:
        if result is not None:
            return True, f"got {result!r}"
        return False, "expected non-None, got None"

    # No expectation defined, just check it doesn't crash
    return True, f"got {result!r} (no assertion)"
