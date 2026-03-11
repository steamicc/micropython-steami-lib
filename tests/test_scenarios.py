"""Generic pytest runner that loads YAML scenarios and executes them."""

import yaml
from pathlib import Path

import pytest

from tests.fake_machine.i2c import FakeI2C
from tests.runner.executor import (
    check_result,
    cleanup_driver,
    load_driver_mock,
    run_action,
)

SCENARIOS_DIR = Path(__file__).parent / "scenarios"


def _print_result(result, test):
    """Print the measured value for report capture."""
    if isinstance(result, float):
        print(f"{result:.2f}")
    elif isinstance(result, int) and "expect" in test and isinstance(test["expect"], int) and test["expect"] > 0xFF:
        print(f"0x{result:04X}")
    elif isinstance(result, int) and (test.get("action") == "read_register" or ("expect" in test and isinstance(test["expect"], int) and test["expect"] >= 0x10)):
        print(f"0x{result:02X}")
    else:
        print(f"{result}")


def iter_scenario_tests():
    """Yield (scenario, test) tuples for parametrize."""
    for yaml_file in sorted(SCENARIOS_DIR.glob("*.yaml")):
        with open(yaml_file, encoding="utf-8") as f:
            scenario = yaml.safe_load(f)

        driver = scenario["driver"]
        for test in scenario.get("tests", []):
            modes = test.get("mode", ["mock", "hardware"])
            for mode in modes:
                test_id = f"{driver}/{test['name']}/{mode}"
                yield pytest.param(scenario, test, mode, id=test_id)


def make_mock_instance(scenario):
    """Create a driver instance using FakeI2C from scenario data."""
    driver_name = scenario["driver"]
    driver_class = scenario["driver_class"]
    address = scenario.get("i2c_address", 0x00)
    mock_registers = scenario.get("mock_registers", {})

    # Convert hex string keys to int if needed
    registers = {}
    for k, v in mock_registers.items():
        key = int(k, 16) if isinstance(k, str) else k
        registers[key] = v

    fake_i2c = FakeI2C(registers=registers, address=address)
    driver_module, _ = load_driver_mock(driver_name, fake_i2c)

    cls = getattr(driver_module, driver_class)
    instance = cls(fake_i2c, address=address)
    return instance, driver_name


@pytest.mark.parametrize("scenario,test,mode", list(iter_scenario_tests()))
def test_scenario(scenario, test, mode, port):
    """Run a single test from a YAML scenario."""
    if mode == "hardware":
        pytest.importorskip("subprocess")
        if port is None:
            pytest.skip("no --port provided for hardware test")

        from tests.runner.mpremote_bridge import MpremoteBridge

        bridge = MpremoteBridge(port=port)
        action = test["action"]

        if action == "manual":
            # Skip manual tests when stdin is not available (no -s flag)
            import sys
            if not sys.stdin.isatty():
                pytest.skip("manual test requires interactive mode (-s)")

            # Display values before prompting if 'display' is defined
            for display in test.get("display", []):
                value = bridge.call_method(
                    scenario["driver"],
                    scenario["driver_class"],
                    scenario["i2c"],
                    display["method"],
                    display.get("args"),
                )
                label = display.get("label", display["method"])
                unit = display.get("unit", "")
                if isinstance(value, float):
                    print(f"  {label}: {value:.2f} {unit}")
                else:
                    print(f"  {label}: {value} {unit}")
            prompt = test.get("prompt", "Manual check")
            response = input(f"  [MANUAL] {prompt} [y/n] ")
            result = response.strip().lower() == "y"
        elif action == "call":
            result = bridge.call_method(
                scenario["driver"],
                scenario["driver_class"],
                scenario["i2c"],
                test["method"],
                test.get("args"),
            )
        elif action == "read_register":
            result = bridge.read_register(
                scenario["i2c"],
                scenario["i2c_address"],
                test["register"],
            )
        else:
            pytest.fail(f"Unknown action: {action}")

        passed, msg = check_result(result, test)
        # Print measured value for the report
        _print_result(result, test)
        assert passed, msg

    elif mode == "mock":
        driver_name = scenario["driver"]
        try:
            instance, _ = make_mock_instance(scenario)
            result = run_action(test, instance)
            passed, msg = check_result(result, test)
            _print_result(result, test)
            assert passed, msg
        finally:
            cleanup_driver(driver_name)
    else:
        pytest.fail(f"Unknown mode: {mode}")
