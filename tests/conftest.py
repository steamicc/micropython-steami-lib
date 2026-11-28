"""Pytest configuration and fixtures for driver testing."""

from pathlib import Path

import pytest
import yaml

pytest_plugins = ["tests.report_plugin"]


def pytest_addoption(parser):
    parser.addoption(
        "--port",
        action="store",
        default=None,
        help="Serial port for hardware tests (e.g. /dev/ttyACM0)",
    )
    parser.addoption(
        "--driver",
        action="store",
        default=None,
        help="Run tests for a specific driver only (e.g. wsen-hids)",
    )
    parser.addoption(
        "--release",
        action="store",
        default=None,
        choices=("V1a", "V1b", "V1c"),
        help="STeaMi release of the board (default: found by Steami.begin() on the board)",
    )


def pytest_collection_modifyitems(config, items):
    port = config.getoption("--port")
    driver = config.getoption("--driver")
    skip_hardware = pytest.mark.skip(reason="needs --port to run hardware tests")

    selected = []
    for item in items:
        # Filter by driver if --driver is specified
        if driver and f"[{driver}/" not in item.nodeid:
            continue
        if "hardware" in item.keywords and not port:
            item.add_marker(skip_hardware)
        selected.append(item)

    items[:] = selected


@pytest.fixture
def port(request):
    return request.config.getoption("--port")


@pytest.fixture(scope="session")
def board_release(request):
    """Return the STeaMi release of the board on --port, found once per session.

    --release gives it without touching the board. Otherwise Steami.begin()
    of lib/steami runs on the board; "" when it cannot tell.
    """
    from tests.runner.release import UNKNOWN, detect_release

    forced = request.config.getoption("--release")
    if forced is not None:
        print(f"\n[STeaMi] Board {forced} (forced by --release)")
        return forced

    from tests.runner.mpremote_bridge import PROJECT_ROOT, MpremoteBridge

    bridge = MpremoteBridge(port=request.config.getoption("--port"))
    release = detect_release(bridge, PROJECT_ROOT / "lib")
    if release == UNKNOWN:
        print("\n[STeaMi] Board release unknown: tests limited to a release are skipped")
    else:
        print(f"\n[STeaMi] Board {release} (found by Steami.begin())")
    return release


def load_scenarios():
    """Load all YAML scenario files from tests/scenarios/."""
    scenarios_dir = Path(__file__).parent / "scenarios"
    scenarios = []
    for yaml_file in sorted(scenarios_dir.glob("*.yaml")):
        with open(yaml_file, encoding="utf-8") as f:
            scenario = yaml.safe_load(f)
            scenario["_file"] = yaml_file.name
            scenarios.append(scenario)
    return scenarios


@pytest.fixture
def mpremote_bridge(port):
    """Create a MpremoteBridge connected to the board."""
    from tests.runner.mpremote_bridge import MpremoteBridge

    return MpremoteBridge(port=port)
