"""Validate example files: syntax, method names, and basic consistency."""

import ast
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
        driver_methods = _discover_driver_methods(driver_dir)
        if not driver_methods:
            pytest.skip(f"No device.py found in {driver_dir.name}")

        source = example_path.read_text(encoding="utf-8")

        # Only check methods that look like driver calls:
        # exclude Python builtins and common MicroPython methods
        # Methods that are NOT from the driver but may appear on
        # driver variables due to MicroPython patterns or inheritance.
        # Keep this list minimal — only names that cause false positives.
        non_driver_methods = {
            "sleep_ms", "sleep_us", "ticks_ms", "ticks_us", "ticks_diff",
            "collect", "mem_free", "mem_alloc",
        }

        # Find the driver class name to identify which variable holds it
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return  # Covered by test_syntax_valid
        driver_imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and any(
                    part in driver_dir.name.replace("-", "_")
                    for part in (node.module.split(".")[0],)
                ):
                    for alias in node.names:
                        driver_imports.add(alias.asname or alias.name)

        if not driver_imports:
            pytest.skip(f"No driver import found in {example_path.name}")

        # Find `variable.method()` patterns where variable
        # is assigned from a driver constructor
        driver_vars = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call):
                    func = node.value.func
                    func_name = None
                    if isinstance(func, ast.Name):
                        func_name = func.id
                    elif isinstance(func, ast.Attribute):
                        func_name = func.attr
                    if func_name in driver_imports:
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                driver_vars.add(target.id)

        if not driver_vars:
            pytest.skip(
                f"Could not identify driver variable in {example_path.name}"
            )

        # Now find method calls on driver variables that don't exist
        missing = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                obj = node.func.value
                if isinstance(obj, ast.Name) and obj.id in driver_vars:
                    method = node.func.attr
                    if method not in driver_methods and method not in non_driver_methods:
                        missing.append((node.lineno, method))

        if missing:
            details = ", ".join(
                f"line {line}: .{method}()" for line, method in missing
            )
            pytest.fail(
                f"{example_path.name} calls methods not found in "
                f"{driver_dir.name}/device.py: {details}"
            )
