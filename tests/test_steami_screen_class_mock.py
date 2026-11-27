"""Tests of steami.Screen and Steami.display(): the board screen on every release."""

import sys

import pytest

from tests.fake_machine import FakePin, FakeSPI
from tests.test_steami_board_mock import (  # noqa: F401 (board_module is a fixture)
    ROOT,
    Setup,
    board_module,
)

V1AB = "V1a/V1b"
SCREEN_PACKAGES = ("gc9a01", "ssd1327", "steami_screen")
E30 = (
    "[STeaMi] Screen: cannot tell if this board is a V1a/V1b or a V1c. "
    'Call Steami.begin("V1c") (or "V1b") at the start of the program. (E30)'
)
E31 = (
    "[STeaMi] Screen: not enough RAM for the screen ({} bytes in one block). "
    "Call begin() on the Screen first in the program. (E31)"
)


def _forget_screen_packages():
    for mod in list(sys.modules):
        if mod.startswith(SCREEN_PACKAGES):
            del sys.modules[mod]


class Hardware:
    """Records every SPI bus and pin created through machine."""

    def __init__(self, machine):
        self.created = []
        self.spis = []
        hardware = self

        class SPI(FakeSPI):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                hardware.created.append(("SPI", args))
                hardware.spis.append(self)

        class Pin(FakePin):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                hardware.created.append(("Pin", args))

        machine.SPI = SPI
        machine.Pin = Pin

    def commands(self):
        return [cmd for spi in self.spis for cmd, _ in spi.commands()]


@pytest.fixture
def screen_env(board_module, monkeypatch):  # noqa: F811 (the imported fixture)
    """The board and const modules, the Screen class and the hardware recorder."""
    for name in SCREEN_PACKAGES:
        path = str(ROOT / "lib" / name)
        if path not in sys.path:
            sys.path.insert(0, path)
    _forget_screen_packages()
    hardware = Hardware(sys.modules["machine"])
    import gc9a01.device

    monkeypatch.setattr(gc9a01.device, "sleep_ms", lambda ms: None)
    from steami.screen import Screen

    yield board_module, Screen, hardware
    _forget_screen_packages()


def board_for(env, release="V1c"):
    """A board whose release is forced, or unknown with release=None."""
    module, _, _ = env
    if release is None:
        missing = ("WSEN-HIDS", "WSEN-PADS", "APDS-9960")
        s = Setup(module, V1AB, missing=missing, config="", zone=False)
        assert s.steami.begin() == ""
    else:
        s = Setup(module)
        s.steami.begin(release)
    s.lines.clear()
    return s


def messages(s):
    return [line for line in s.lines if not line.startswith("[STeaMi] Board")]


def draw_everything(screen):
    """Every call of the drawing API; returns the results of show()."""
    screen.clear()
    screen.title("Title")
    screen.value(21.5, unit="C", label="T")
    screen.subtitle("one", "two")
    screen.bar(40)
    screen.gauge(30)
    screen.graph([1, 5, 3, 8])
    screen.menu(["a", "b", "c"], selected=1)
    screen.compass(90)
    screen.watch(10, 30, 15)
    screen.face("happy")
    screen.text("Hi", at="NE")
    screen.text("xy", at=(3, 4))
    screen.line(0, 0, 10, 10)
    screen.circle(20, 20, 5, fill=True)
    screen.rect(1, 1, 8, 8)
    screen.pixel(2, 2)
    return screen.show()


# --------------------------------------------------
# Routing
# --------------------------------------------------


def test_mock_screen_v1c_is_the_gc9a01(screen_env):
    (_, const), screen_cls, hardware = screen_env
    s = board_for(screen_env, "V1c")
    screen = screen_cls()
    assert screen.begin() is True
    assert screen.chip() == "GC9A01"
    assert (screen.width, screen.height) == (240, 240)
    assert (screen.center, screen.radius, screen.k) == ((120, 120), 120, 2)
    assert screen.is_available() is True
    assert screen.status() == const.Status.OK
    assert screen.error() == ""
    from steami_screen import GC9A01Display

    assert isinstance(s.steami.display(), GC9A01Display)
    assert ("SPI", (1,)) in hardware.created
    assert {args for kind, args in hardware.created if kind == "Pin"} == {
        ("CS_DISPLAY",),
        ("DATA_COMMAND_DISPLAY",),
        ("RST_DISPLAY",),
    }
    assert messages(s) == []


@pytest.mark.parametrize("release", ["V1a", "V1b"])
def test_mock_screen_v1ab_is_the_ssd1327(screen_env, release):
    (_, const), screen_cls, _ = screen_env
    s = board_for(screen_env, release)
    screen = screen_cls()
    assert screen.begin() is True
    assert screen.chip() == "SSD1327"
    assert (screen.width, screen.height, screen.k) == (128, 128, 1)
    from steami_screen import SSD1327Display

    assert isinstance(s.steami.display(), SSD1327Display)
    assert messages(s) == []


def test_mock_screen_route_and_has(screen_env):
    (_, const), _, _ = screen_env
    f, c, r = const.Function, const.Chip, const.Release
    assert f.SCREEN == "screen"
    assert (c.SSD1327, c.GC9A01) == ("SSD1327", "GC9A01")
    assert const.route(r.V1A, f.SCREEN) == (c.SSD1327,)
    assert const.route(r.V1AB, f.SCREEN) == (c.SSD1327,)
    assert const.route(r.V1C, f.SCREEN) == (c.GC9A01,)
    assert const.route(r.UNKNOWN, f.SCREEN) == ()
    assert (const.E_SCREEN_UNKNOWN_BOARD, const.E_NO_MEMORY) == ("E30", "E31")
    assert const.Status.NO_MEMORY == "no memory"
    s = board_for(screen_env, "V1c")
    assert s.steami.has(f.SCREEN) is True


def test_mock_screen_draws_on_the_v1c_panel(screen_env):
    _, screen_cls, hardware = screen_env
    s = board_for(screen_env, "V1c")
    screen = screen_cls()
    screen.title("Hello")
    raw = s.steami.display()._raw
    assert any(raw.buffer)
    hardware.spis[0].clear()
    assert screen.show() is None
    assert 0x2C in hardware.commands()  # RAMWR: a frame was sent


def test_mock_first_use_begins(screen_env):
    _, screen_cls, _ = screen_env
    s = board_for(screen_env, "V1c")
    screen = screen_cls()
    assert screen.width == 240  # the first use starts the screen
    assert screen.is_available() is True
    s.lines.clear()
    screen_cls().pixel(1, 1)
    assert messages(s) == []


# --------------------------------------------------
# Shared adapter
# --------------------------------------------------


def test_mock_display_is_shared(screen_env, monkeypatch):
    _, screen_cls, hardware = screen_env
    import gc9a01.device

    inits = []
    init = gc9a01.device.GC9A01.init
    monkeypatch.setattr(gc9a01.device.GC9A01, "init", lambda raw: inits.append(init(raw)))
    s = board_for(screen_env, "V1c")
    first = s.steami.display()
    assert first is not None
    assert s.steami.display() is first
    a, b = screen_cls(), screen_cls()
    a.begin()
    b.begin()
    assert a._d is first
    assert b._d is first
    assert len(inits) == 1  # the panel was set up once
    assert sum(1 for kind, _ in hardware.created if kind == "SPI") == 1


def test_mock_display_kept_after_a_forced_release(screen_env):
    s = board_for(screen_env, "V1c")
    first = s.steami.display()
    s.steami.begin("V1b")
    assert s.steami.display() is first


def test_mock_end_forgets_the_display(screen_env):
    s = board_for(screen_env, "V1c")
    first = s.steami.display()
    s.steami.end()
    s.steami.begin("V1c")
    assert s.steami.display() is not first


# --------------------------------------------------
# No hardware on creation, lazy imports
# --------------------------------------------------


def test_mock_creating_a_screen_touches_nothing(screen_env):
    (module, const), screen_cls, hardware = screen_env
    s = Setup((module, const))  # release not detected yet
    screen = screen_cls()
    assert hardware.created == []
    assert s.reads == []
    assert s.steami._detected is False
    assert screen.status() == const.Status.NOT_STARTED
    assert screen.error() == "not started"
    assert screen.chip() == ""
    assert screen.is_available() is False


def test_mock_import_steami_loads_no_screen(board_module):  # noqa: F811
    for name in SCREEN_PACKAGES:
        path = str(ROOT / "lib" / name)
        if path not in sys.path:
            sys.path.insert(0, path)
    _forget_screen_packages()
    try:
        import steami

        assert not any(m.startswith(SCREEN_PACKAGES) for m in sys.modules)
        screen_class = steami.Screen
        assert screen_class.__name__ == "Screen"
        assert steami.__dict__["Screen"] is screen_class
        assert "steami_screen" in sys.modules
        # The drivers wait for the first display().
        assert "gc9a01" not in sys.modules
        assert "ssd1327" not in sys.modules
    finally:
        _forget_screen_packages()


# --------------------------------------------------
# Unknown release: E30
# --------------------------------------------------


def test_mock_unknown_release_e30(screen_env):
    (_, const), screen_cls, hardware = screen_env
    s = board_for(screen_env, None)
    screen = screen_cls()
    assert screen.begin() is False
    assert screen.status() == const.Status.UNKNOWN_BOARD
    assert screen.error() == "unknown board"
    assert screen.chip() == ""
    assert screen.is_available() is False
    # The default size of steami_screen, so that widgets still lay out.
    assert (screen.width, screen.height) == (128, 128)
    assert s.steami.display() is None
    assert draw_everything(screen) is None
    assert screen_cls().begin() is False
    assert messages(s) == [E30]
    assert s.steami.last_error() == E30
    assert hardware.created == []


# --------------------------------------------------
# Not enough RAM: E31 (Review Focus 4)
# --------------------------------------------------


def _fail_allocation(monkeypatch, module, size):
    """Make the bytearray(size) of a driver module raise MemoryError."""

    def allocate(*args):
        if args and args[0] == size:
            raise MemoryError
        return bytearray(*args)

    monkeypatch.setattr(module, "bytearray", allocate, raising=False)


def test_mock_no_memory_e31_v1c(screen_env, monkeypatch):
    (_, const), screen_cls, _ = screen_env
    import gc9a01.device

    s = board_for(screen_env, "V1c")
    _fail_allocation(monkeypatch, gc9a01.device, 28800)
    screen = screen_cls()
    assert screen.begin() is False
    assert screen.status() == const.Status.NO_MEMORY
    assert screen.error() == "no memory"
    assert screen.chip() == "GC9A01"
    assert screen.is_available() is False
    assert (screen.width, screen.height) == (240, 240)  # the panel's size
    assert s.steami.display() is None
    assert draw_everything(screen) is None
    assert messages(s) == [E31.format(28800)]
    assert screen_cls().begin() is False
    assert messages(s) == [E31.format(28800)]  # once, as E30
    # Once the RAM is free, a new Screen gets the panel.
    monkeypatch.delattr(gc9a01.device, "bytearray")
    again = screen_cls()
    assert again.begin() is True
    assert screen.is_available() is False  # an object keeps its answer


def test_mock_no_memory_e31_v1ab(screen_env, monkeypatch):
    (_, const), screen_cls, _ = screen_env
    import ssd1327.device

    s = board_for(screen_env, "V1b")
    _fail_allocation(monkeypatch, ssd1327.device, 8192)
    screen = screen_cls()
    assert screen.begin() is False
    assert screen.status() == const.Status.NO_MEMORY
    assert screen.chip() == "SSD1327"
    assert screen.width == 128
    assert draw_everything(screen) is None
    assert messages(s) == [E31.format(8192)]


def test_mock_other_memory_error_propagates(screen_env, monkeypatch):
    _, screen_cls, _ = screen_env
    import steami_screen

    class Boom:
        def __init__(self, raw):
            raise MemoryError

    s = board_for(screen_env, "V1c")
    monkeypatch.setattr(steami_screen, "GC9A01Display", Boom)
    with pytest.raises(MemoryError):
        s.steami.display()
    with pytest.raises(MemoryError):
        screen_cls().begin()


def test_mock_unknown_attribute_raises(screen_env):
    _, screen_cls, _ = screen_env
    board_for(screen_env, "V1c")
    screen = screen_cls()
    with pytest.raises(AttributeError):
        screen.nothing  # noqa: B018
    assert not hasattr(screen, "nothing")
