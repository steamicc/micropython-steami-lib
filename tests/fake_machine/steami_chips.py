"""Register images of the chips on the STeaMi internal I2C bus.

The images are the mock_registers of each driver's YAML scenario, so they
hold what the driver constructors read (WHO_AM_I, calibration...).
"""

from pathlib import Path

import yaml

from tests.fake_machine.i2c_bus import FakeI2CBus

ADDRESS = {
    "BME280": 0x76,
    "WSEN-HIDS": 0x5F,
    "WSEN-PADS": 0x5D,
    "APDS-9960": 0x39,
    "VL53L1X": 0x29,
    "ISM330DL": 0x6B,
    "LIS2MDL": 0x1E,
    "BQ27441": 0x55,
    "MCP23009E": 0x20,
    "DAPLINK": 0x3B,
}

_SCENARIO = {
    "BME280": "bme280",
    "WSEN-HIDS": "wsen_hids",
    "WSEN-PADS": "wsen_pads",
    "APDS-9960": "apds9960",
    "VL53L1X": "vl53l1x",
    "ISM330DL": "ism330dl",
    "LIS2MDL": "lis2mdl",
    "BQ27441": "bq27441",
    "MCP23009E": "mcp23009e",
    "DAPLINK": "daplink_bridge",
}

_RELEASES = {
    "V1a/V1b": ("WSEN-HIDS", "WSEN-PADS", "APDS-9960", "VL53L1X", "ISM330DL",
                "LIS2MDL", "BQ27441", "MCP23009E", "DAPLINK"),
    "V1c": ("BME280", "VL53L1X", "ISM330DL", "LIS2MDL", "BQ27441",
            "MCP23009E", "DAPLINK"),
}

_SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"


def image(chip):
    """Return a fresh register image (register -> int or bytes) of a chip."""
    path = _SCENARIOS_DIR / (_SCENARIO[chip] + ".yaml")
    with open(path) as f:
        registers = yaml.safe_load(f)["mock_registers"]
    return {reg: bytes(v) if isinstance(v, list) else v for reg, v in registers.items()}


def board(release, missing=()):
    """Return a FakeI2CBus with the chips of a release, minus `missing`."""
    chips = [c for c in _RELEASES[release] if c not in missing]
    return FakeI2CBus({ADDRESS[c]: image(c) for c in chips})
