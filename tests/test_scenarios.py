"""Generic pytest runner that loads YAML scenarios and executes them."""

import yaml
from pathlib import Path

import pytest

from tests.fake_machine.i2c import FakeI2C
from tests.fake_machine.pin import FakePin
from tests.runner.executor import (
    check_result,
    cleanup_driver,
    load_driver_mock,
    prompt_yes_no,
    run_action,
)

SCENARIOS_DIR = Path(__file__).parent / "scenarios"


def _print_result(result, test):
    """Print the measured value for report capture."""
    if isinstance(result, bool):
        # Boolean smoke tests (True/False) — nothing useful to print
        return
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

        is_board = scenario.get("type") == "board"
        name = scenario.get("name", scenario.get("driver", yaml_file.stem))
        for test in scenario.get("tests", []):
            modes = test.get("mode", ["mock", "hardware"])
            if is_board:
                # Board scenarios are hardware-only
                modes = [m for m in modes if m == "hardware"]
            for mode in modes:
                test_id = f"{name}/{test['name']}/{mode}"
                marks = [pytest.mark.board, pytest.mark.hardware] if is_board else []
                yield pytest.param(scenario, test, mode, id=test_id, marks=marks)


def make_mock_instance(scenario):
    """Create a driver instance using FakeI2C from scenario data."""
    driver_name = scenario["driver"]
    module_name = scenario.get("module_name", driver_name)
    driver_class = scenario["driver_class"]
    address = scenario.get("i2c_address", 0x00)
    mock_registers = scenario.get("mock_registers", {})

    # Convert hex string keys to int if needed
    registers = {}
    for k, v in mock_registers.items():
        key = int(k, 16) if isinstance(k, str) else k
        registers[key] = v

    fake_i2c = FakeI2C(registers=registers, address=address)
    driver_module, _ = load_driver_mock(driver_name, fake_i2c, module_name=module_name)

    # Build extra constructor kwargs from mock_pins
    extra_kwargs = {}
    for pin_name, pin_id in scenario.get("mock_pins", {}).items():
        extra_kwargs[pin_name] = FakePin(pin_id)

    cls = getattr(driver_module, driver_class)
    instance = cls(fake_i2c, address=address, **extra_kwargs)
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

        is_board = scenario.get("type") == "board"

        if action == "manual":
            # Skip manual tests when stdin is not available (no -s flag)
            import sys
            if not sys.stdin.isatty():
                pytest.skip("manual test requires interactive mode (-s)")

            # Display values before prompting if 'display' is defined
            # (board scenarios have no driver, so display is not supported)
            if not is_board:
                for display in test.get("display", []):
                    value = bridge.call_method(
                        scenario["driver"],
                        scenario["driver_class"],
                        scenario["i2c"],
                        display["method"],
                        display.get("args"),
                        module_name=scenario.get("module_name"),
                        hardware_init=scenario.get("hardware_init"),
                        i2c_address=scenario.get("i2c_address"),
                    )
                    label = display.get("label", display["method"])
                    unit = display.get("unit", "")
                    if isinstance(value, float):
                        print(f"  {label}: {value:.2f} {unit}")
                    else:
                        print(f"  {label}: {value} {unit}")
            prompt = test.get("prompt", "Manual check")
            result = prompt_yes_no(prompt)
        elif action in ("call", "read_register", "interactive"):
            if is_board:
                pytest.fail(
                    f"Board scenarios do not support '{action}' action; "
                    f"use 'hardware_script' or 'manual' instead"
                )
            if action == "call":
                result = bridge.call_method(
                    scenario["driver"],
                    scenario["driver_class"],
                    scenario["i2c"],
                    test["method"],
                    test.get("args"),
                    module_name=scenario.get("module_name"),
                    hardware_init=scenario.get("hardware_init"),
                    i2c_address=scenario.get("i2c_address"),
                )
            elif action == "read_register":
                result = bridge.read_register(
                    scenario["i2c"],
                    scenario["i2c_address"],
                    test["register"],
                )
            else:  # interactive
                import sys
                if not sys.stdin.isatty():
                    pytest.skip("interactive test requires interactive mode (-s)")
                pre_prompt = test.get("pre_prompt", "Perform action then press Enter")
                input(f"  [INTERACTIVE] {pre_prompt} ")
                result = bridge.call_method(
                    scenario["driver"],
                    scenario["driver_class"],
                    scenario["i2c"],
                    test["method"],
                    test.get("args"),
                    module_name=scenario.get("module_name"),
                    hardware_init=scenario.get("hardware_init"),
                    i2c_address=scenario.get("i2c_address"),
                )
        elif action == "hardware_script":
            import sys
            if not sys.stdin.isatty():
                pytest.skip("hardware_script test requires interactive mode (-s)")
            pre_prompt = test.get("pre_prompt")
            if pre_prompt:
                if test.get("wait", True):
                    input(f"  [INTERACTIVE] {pre_prompt} ")
                else:
                    print(f"  [INTERACTIVE] {pre_prompt}")
            if is_board:
                mount_dir = None
                if scenario.get("drivers"):
                    mount_dir = Path(__file__).parent.parent / "lib"
                result = bridge.run_raw_script(
                    test["script"], mount_dir=mount_dir,
                )
            else:
                result = bridge.run_script(
                    scenario["driver"],
                    scenario["driver_class"],
                    scenario["i2c"],
                    test["script"],
                    module_name=scenario.get("module_name"),
                    hardware_init=scenario.get("hardware_init"),
                    i2c_address=scenario.get("i2c_address"),
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
