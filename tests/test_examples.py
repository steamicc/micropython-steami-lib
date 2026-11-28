"""Validate example files: syntax, method names, and basic consistency."""

import ast
import importlib.util
import sys
import time
import types
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent / "lib"


def _discover_examples():
    """Yield (driver_dir, example_path) for every example file."""
    for driver_dir in sorted(LIB_DIR.iterdir()):
        examples_dir = driver_dir / "examples"
        if not examples_dir.is_dir():
            continue
        for example in sorted(examples_dir.glob("*.py")):
            yield driver_dir, example


def _discover_driver_methods(driver_dir):
    """Return the set of all method names from a driver's Python files."""
    # Find the module directory (may differ from driver dir name)
    module_dirs = [
        d for d in driver_dir.iterdir()
        if d.is_dir() and (d / "device.py").exists()
    ]
    if not module_dirs:
        return set()

    # Prefer module dir matching driver name, else first alphabetically.
    driver_module = driver_dir.name.replace("-", "_")
    preferred = next((d for d in module_dirs if d.name == driver_module), None)
    module_dir = preferred or sorted(module_dirs, key=lambda d: d.name)[0]

    methods = set()
    # Scan all .py files in the module (device.py, pin.py, etc.)
    for py_file in module_dir.glob("*.py"):
        if py_file.name == "__init__.py" or py_file.name == "const.py":
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError as e:
            pytest.fail(f"Syntax error in driver {py_file}: {e}")

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.add(item.name)
    return methods


STEAMI_PKG = LIB_DIR / "steami" / "steami"

# Methods that are NOT from the driver but may appear on driver variables due
# to MicroPython patterns. Keep this list minimal: only names that cause false
# positives. The steami classes get their own methods (_steami_class_methods).
NON_DRIVER_METHODS = {
    "sleep_ms", "sleep_us", "ticks_ms", "ticks_us", "ticks_diff",
    "collect", "mem_free", "mem_alloc",
}


def _class_methods(node):
    """Names of the methods defined in the body of a ClassDef node."""
    return {
        item.name
        for item in node.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _steami_class_methods():
    """Return {class name: method names} for every class of the steami package.

    A class gets its own methods, those of its steami bases (Handle) and,
    for a base imported from another driver (steami.Screen subclasses
    steami_screen.Screen), every method of that driver.
    """
    own, bases = {}, {}
    for py_file in sorted(STEAMI_PKG.glob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        drivers = {}  # local name -> driver dir, for names imported from one
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                if root != "steami" and (LIB_DIR / root).is_dir():
                    for alias in node.names:
                        drivers[alias.asname or alias.name] = LIB_DIR / root
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                own[node.name] = _class_methods(node)
                bases[node.name] = [
                    drivers.get(base.id, base.id)
                    for base in node.bases
                    if isinstance(base, ast.Name)
                ]

    def resolve(name):
        methods = set(own[name])
        for base in bases[name]:
            if isinstance(base, Path):
                methods |= _discover_driver_methods(base)
            elif base in own:
                methods |= resolve(base)
        return methods

    return {name: resolve(name) for name in own}


def _check_driver_calls(driver_dir, source):
    """Return (skip reason, [(line, method)]) for the driver calls of source.

    A variable assigned from a name imported from the driver may call any
    method of the driver; one assigned from a steami class (from steami
    import Screen, Distance...) only the methods of that class. The skip
    reason is None when the check ran. lib/steami has no device.py: its
    examples are checked against the steami classes alone.
    """
    driver_methods = _discover_driver_methods(driver_dir)
    if not driver_methods and driver_dir.name != "steami":
        return f"No device.py found in {driver_dir.name}", []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return "Syntax error (covered by test_syntax_valid)", []

    # Names imported from the driver, each with the methods its objects have.
    steami_methods = None
    driver_imports = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root not in driver_dir.name.replace("-", "_"):
                continue
            for alias in node.names:
                methods = driver_methods
                if root == "steami":
                    if steami_methods is None:
                        steami_methods = _steami_class_methods()
                    methods = steami_methods.get(alias.name, set())
                driver_imports[alias.asname or alias.name] = methods

    if not driver_imports:
        return "No driver import found", []

    # Variables assigned from a driver constructor, with their methods.
    driver_vars = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            func = node.value.func
            func_name = None
            if isinstance(func, ast.Name):
                func_name = func.id
            elif isinstance(func, ast.Attribute):
                func_name = func.attr
            if func_name in driver_imports:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        driver_vars[target.id] = driver_imports[func_name]

    if not driver_vars:
        return "Could not identify driver variable", []

    missing = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            obj = node.func.value
            if isinstance(obj, ast.Name) and obj.id in driver_vars:
                method = node.func.attr
                if method not in driver_vars[obj.id] and method not in NON_DRIVER_METHODS:
                    missing.append((node.lineno, method))
    return None, sorted(missing)


# Build test parameters
_examples = list(_discover_examples())


@pytest.mark.parametrize(
    "driver_dir,example_path",
    _examples,
    ids=[f"{d.name}/{e.name}" for d, e in _examples],
)
class TestExampleValidation:
    """Validate each example file."""

    def test_syntax_valid(self, driver_dir, example_path):
        """Example file must be valid Python syntax."""
        source = example_path.read_text(encoding="utf-8")
        try:
            compile(source, str(example_path), "exec")
        except SyntaxError as e:
            pytest.fail(f"Syntax error in {example_path}: {e}")

    def test_has_final_newline(self, driver_dir, example_path):
        """Example file should end with a newline."""
        content = example_path.read_bytes()
        if content and content[-1:] != b"\n":
            pytest.fail(f"{example_path.name} is missing a final newline")

    def test_no_bare_except(self, driver_dir, example_path):
        """Example should not use bare except: (project convention)."""
        source = example_path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return  # Covered by test_syntax_valid

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                pytest.fail(
                    f"{example_path.name}:{node.lineno} uses bare 'except:' "
                    f"— use 'except Exception:' instead"
                )

    def test_method_calls_exist_in_driver(self, driver_dir, example_path):
        """Method calls on driver objects should match actual driver API."""
        skip, missing = _check_driver_calls(
            driver_dir, example_path.read_text(encoding="utf-8")
        )
        if skip:
            pytest.skip(f"{skip} in {example_path.name}")
        if missing:
            details = ", ".join(
                f"line {line}: .{method}()" for line, method in missing
            )
            pytest.fail(
                f"{example_path.name} calls methods not found in "
                f"{driver_dir.name}/device.py: {details}"
            )


# ----- The driver-call check itself -----


def _calls(driver, source):
    """(skip reason, missing calls) of the driver-call check on source."""
    return _check_driver_calls(LIB_DIR / driver, source)


def test_steami_screen_object_may_not_call_a_sensor_method():
    # steami.Screen has begin() (Handle) and the steami_screen drawing API,
    # but no read(): only the steami classes that have it may call it.
    source = (
        "from steami import Screen\n"
        "screen = Screen()\n"
        "screen.begin()\n"
        "screen.title('Hi')\n"
        "screen.chip()\n"
        "screen.read()\n"
    )
    assert _calls("steami_screen", source) == (None, [(6, "read")])


def test_steami_sensor_object_gets_its_own_class_methods_only():
    source = (
        "from steami import Distance\n"
        "distance = Distance()\n"
        "distance.begin()\n"
        "distance.is_available()\n"
        "distance.read()\n"
        "distance.cm()\n"
        "distance.title('Hi')\n"
    )
    assert _calls("steami_screen", source) == (None, [(7, "title")])


def test_steami_examples_are_checked_against_the_steami_classes():
    # lib/steami has no device.py: its examples use the class methods only.
    source = (
        "from steami import Temperature\n"
        "temperature = Temperature()\n"
        "temperature.read()\n"
        "temperature.set_offset(1)\n"
        "temperature.cm()\n"
    )
    assert _calls("steami", source) == (None, [(5, "cm")])


def test_other_drivers_do_not_get_the_steami_methods():
    # begin(), status(), chip()... belong to the steami classes, not to the
    # other drivers: a BME280 object calling them is reported.
    source = (
        "from bme280 import BME280\n"
        "sensor = BME280(i2c)\n"
        "sensor.read()\n"
        "sensor.begin()\n"
        "sensor.is_available()\n"
        "sensor.status()\n"
        "sensor.error()\n"
        "sensor.chip()\n"
        "sleep_ms(10)\n"
    )
    assert _calls("bme280", source) == (
        None,
        [(4, "begin"), (5, "is_available"), (6, "status"), (7, "error"), (8, "chip")],
    )


def test_steami_classes_inherit_handle_and_the_wrapped_driver():
    methods = _steami_class_methods()
    assert {"begin", "is_available", "status", "error", "chip"} <= methods["Distance"]
    assert {"read", "cm"} <= methods["Distance"]
    assert "title" not in methods["Distance"]
    # steami.Screen(Handle, steami_screen.Screen)
    assert {"begin", "title", "gauge", "show"} <= methods["Screen"]
    assert "read" not in methods["Screen"]


# ----- Example-specific checks -----


def test_compass_demo_smooths_the_heading():
    # The raw LIS2MDL heading jitters by a few degrees on a still board
    # (#371): the demo must turn on the heading low-pass filter, with the
    # same alpha as the Arduino DigitalCompass example (setHeadingFilter(0.2f)).
    path = LIB_DIR / "steami_screen" / "examples" / "compass_demo.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    alphas = [
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "set_heading_filter"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    ]
    assert alphas == [0.2]


def _load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _weather_station_gauge_colors(monkeypatch, v1c):
    """Run weather_station.py for one loop on page 1; the gauge colours drawn.

    The steami classes are fakes: RIGHT is pressed once, so the first loop
    draws the Humidity page, and sleep_ms() then stops the program.
    """
    from tests.fake_machine import micropython_stub

    monkeypatch.setitem(sys.modules, "micropython", micropython_stub)
    screen_dir = LIB_DIR / "steami_screen" / "steami_screen"
    const = _load_file("_weather_const", screen_dir / "const.py")
    gauges = []

    class Part:
        RIGHT = "right"

        def __getattr__(self, name):
            return lambda *args, **kwargs: None

        def begin(self):
            return True

        def read(self):
            return 50.0

        def heading(self):
            return 0.0

    class Screen(Part):
        def gauge(self, value, **kwargs):
            gauges.append(kwargs["color"])

    class Buttons(Part):
        pressed = ["RIGHT"]

        def was_pressed(self, name):
            if name in self.pressed:
                self.pressed.remove(name)
                return True
            return False

    class Gesture(Part):
        def begin(self):
            return not v1c

    class Board:
        def is_v1c(self):
            return v1c

        def print_info(self):
            pass

    steami = types.ModuleType("steami")
    steami.Screen, steami.Buttons, steami.Gesture = Screen, Buttons, Gesture
    steami.Temperature = steami.Humidity = steami.Pressure = steami.Compass = Part
    steami.Steami = Board()
    steami_screen = types.ModuleType("steami_screen")
    for name in ("BLACK", "DARK", "GRAY", "LIGHT", "WHITE", "GREEN", "RED", "BLUE"):
        setattr(steami_screen, name, getattr(const, name))
    monkeypatch.setitem(sys.modules, "steami", steami)
    monkeypatch.setitem(sys.modules, "steami_screen", steami_screen)

    def stop(ms):
        raise KeyboardInterrupt

    monkeypatch.setattr(time, "sleep_ms", stop, raising=False)
    path = LIB_DIR / "steami" / "examples" / "weather_station.py"
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), {"__name__": "__main__"})
    return const, gauges


def test_weather_station_gauge_stands_out_from_its_track_on_the_grey_screen(monkeypatch):
    # gauge() draws its track in DARK (grey 6). BLUE is grey 6 too on the
    # SSD1327, so the filled arc would not show: on V1a/V1b the example
    # lifts it to grey 10, as the Arduino WeatherStation example (5.10).
    const, gauges = _weather_station_gauge_colors(monkeypatch, v1c=False)
    colors = _load_file(
        "_weather_colors", LIB_DIR / "steami_screen" / "steami_screen" / "colors.py"
    )
    assert len(gauges) == 1
    assert colors.rgb_to_gray4(gauges[0]) == 10
    assert colors.rgb_to_gray4(gauges[0]) - colors.rgb_to_gray4(const.DARK) >= 3


def test_weather_station_gauge_is_blue_on_the_colour_screen(monkeypatch):
    const, gauges = _weather_station_gauge_colors(monkeypatch, v1c=True)
    assert gauges == [const.BLUE]
