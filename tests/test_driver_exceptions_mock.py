"""Mock tests of the driver exception convention (issues #319 and #320).

Each driver error class derives from OSError, through a base class named
after the driver (XxxError(OSError)). Simple code catches every hardware
error with ``except OSError``; precise code catches the driver class.
Timeouts are OSError subclasses too. Invalid arguments raise ValueError.
"""

import ast
import importlib
import inspect
from pathlib import Path

import pytest

from tests.fake_machine import FakeI2C
from tests.runner.executor import cleanup_driver, load_driver_mock

LIB = Path(__file__).parent.parent / "lib"

# (driver directory, module, base class)
DRIVERS = [
    ("apds9960", "apds9960", "APDS9960Error"),
    ("bme280", "bme280", "BME280Error"),
    ("ism330dl", "ism330dl", "ISM330DLError"),
    ("wsen-hids", "wsen_hids", "WSENHIDSError"),
    ("wsen-pads", "wsen_pads", "WSENPADSError"),
]

# Argument errors, not chip errors: they stay ValueError.
ARGUMENT_ERRORS = {"APDS9960InvalidMode"}


@pytest.fixture
def exceptions_of():
    loaded = []

    def load(driver, module):
        load_driver_mock(driver, FakeI2C(), module)
        loaded.append((driver, module))
        return importlib.import_module(module + ".exceptions")

    yield load
    for driver, module in loaded:
        cleanup_driver(driver, module)


def _classes(mod):
    return [
        cls
        for _, cls in inspect.getmembers(mod, inspect.isclass)
        if issubclass(cls, BaseException) and cls.__module__ == mod.__name__
    ]


@pytest.mark.parametrize(("driver", "module", "base"), DRIVERS)
def test_mock_driver_base_error_is_oserror(exceptions_of, driver, module, base):
    mod = exceptions_of(driver, module)
    assert issubclass(getattr(mod, base), OSError)


@pytest.mark.parametrize(("driver", "module", "base"), DRIVERS)
def test_mock_driver_errors_derive_from_base(exceptions_of, driver, module, base):
    mod = exceptions_of(driver, module)
    base_cls = getattr(mod, base)
    for cls in _classes(mod):
        if cls.__name__ in ARGUMENT_ERRORS:
            assert issubclass(cls, ValueError), cls.__name__
        else:
            assert issubclass(cls, base_cls), cls.__name__


@pytest.mark.parametrize(
    ("driver", "module", "name"),
    [
        ("wsen-hids", "wsen_hids", "WSENHIDSTimeoutError"),
        ("wsen-pads", "wsen_pads", "WSENPADSTimeout"),
    ],
)
def test_mock_timeout_errors_are_oserror(exceptions_of, driver, module, name):
    mod = exceptions_of(driver, module)
    error = getattr(mod, name)("data ready timeout")
    assert isinstance(error, OSError)
    assert str(error) == "data ready timeout"


def _micropython_missing_calls(tree):
    """Calls that fail on the MicroPython port of the board.

    Exception.__init__(self, ...) and OSError.__init__(self, ...) raise
    AttributeError, and the format() builtin is not built in: the driver
    error would turn into another one. super().__init__() and str.format()
    work.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "__init__"
            and isinstance(func.value, ast.Name)
            and func.value.id.endswith(("Exception", "Error"))
        ):
            yield func.value.id + ".__init__"
        elif isinstance(func, ast.Name) and func.id == "format":
            yield "format"


@pytest.mark.parametrize(
    "path", sorted(LIB.glob("*/*/exceptions.py")), ids=lambda p: p.parent.name
)
def test_mock_exceptions_use_micropython_builtins_only(path):
    tree = ast.parse(path.read_text())
    assert list(_micropython_missing_calls(tree)) == []


@pytest.fixture
def apds9960():
    yield lambda registers: load_driver_mock(
        "apds9960", FakeI2C(registers=registers, address=0x39)
    )
    cleanup_driver("apds9960")


def test_mock_apds9960_wrong_id_raises_oserror(apds9960):
    device, i2c = apds9960({0x92: 0x12})
    exceptions = importlib.import_module("apds9960.exceptions")
    with pytest.raises(exceptions.APDS9960Error) as info:
        device.uAPDS9960(i2c)
    assert isinstance(info.value, OSError)
    assert isinstance(info.value, exceptions.APDS9960InvalidDevId)
    assert "0x12" in str(info.value)
    assert "0xab" in str(info.value)


def test_mock_apds9960_invalid_mode_raises_value_error(apds9960):
    device, i2c = apds9960({0x92: 0xAB})
    sensor = device.uAPDS9960(i2c)
    with pytest.raises(ValueError, match="9"):
        sensor.set_mode(9)


@pytest.fixture
def vl53l1x():
    yield lambda registers: load_driver_mock("vl53l1x", FakeI2C(registers=registers, address=0x29))
    cleanup_driver("vl53l1x")


def test_mock_vl53l1x_wrong_id_raises_oserror(vl53l1x):
    device, i2c = vl53l1x({0x010F: [0x12, 0x34], 0x0000: 0x01})
    with pytest.raises(OSError, match="VL53L1X"):
        device.VL53L1X(i2c)
