"""Mock tests of the gc9a01 driver (STeaMi V1c round screen).

The driver keeps a 16-colour GS4 frame and converts it to RGB565 while
sending. These tests check the bytes on a FakeSPI: the Arduino init
sequence, the window, the byte order of each palette colour, the size of
each write, and that drawing off screen never raises. show() converts with
a viper function: its writes are compared byte for byte with the palette
blit it replaced, on guarded buffers (viper has no bounds check).
"""

import importlib
import random
import sys

import pytest

from tests.fake_machine import FakePin, FakeSPI
from tests.fake_machine.font_petme128 import FONT_PETME128_8X8
from tests.runner.executor import cleanup_driver, load_driver_mock

WIDTH = 240
HEIGHT = 240
FRAME_BYTES = WIDTH * HEIGHT * 2  # RGB565 on the wire

SWRESET = 0x01
SLPIN = 0x10
SLPOUT = 0x11
DISPOFF = 0x28
DISPON = 0x29
CASET = 0x2A
RASET = 0x2B
RAMWR = 0x2C

# kInitSequence of SteamiGC9A01.cpp (arduino-steami-lib), followed by what
# initDisplay() sends after it: MADCTL (BGR, V1c orientation) and INVON.
ARDUINO_INIT = [
    (0xEF, b""),
    (0xEB, b"\x14"),
    (0xFE, b""),
    (0xEF, b""),
    (0xEB, b"\x14"),
    (0x84, b"\x40"),
    (0x85, b"\xff"),
    (0x86, b"\xff"),
    (0x87, b"\xff"),
    (0x88, b"\x0a"),
    (0x89, b"\x21"),
    (0x8A, b"\x00"),
    (0x8B, b"\x80"),
    (0x8C, b"\x01"),
    (0x8D, b"\x01"),
    (0x8E, b"\xff"),
    (0x8F, b"\xff"),
    (0xB6, b"\x00\x20"),
    (0x3A, b"\x05"),
    (0x90, b"\x08\x08\x08\x08"),
    (0xBD, b"\x06"),
    (0xBC, b"\x00"),
    (0xFF, b"\x60\x01\x04"),
    (0xC3, b"\x13"),
    (0xC4, b"\x13"),
    (0xC9, b"\x22"),
    (0xBE, b"\x11"),
    (0xE1, b"\x10\x0e"),
    (0xDF, b"\x21\x0c\x02"),
    (0xF0, b"\x45\x09\x08\x08\x26\x2a"),
    (0xF1, b"\x43\x70\x72\x36\x37\x6f"),
    (0xF2, b"\x45\x09\x08\x08\x26\x2a"),
    (0xF3, b"\x43\x70\x72\x36\x37\x6f"),
    (0xED, b"\x1b\x0b"),
    (0xAE, b"\x77"),
    (0xCD, b"\x63"),
    (0x70, b"\x07\x07\x04\x0e\x0f\x09\x07\x08\x03"),
    (0xE8, b"\x34"),
    (0x62, b"\x18\x0d\x71\xed\x70\x70\x18\x0f\x71\xef\x70\x70"),
    (0x63, b"\x18\x11\x71\xf1\x70\x70\x18\x13\x71\xf3\x70\x70"),
    (0x64, b"\x28\x29\xf1\x01\xf1\x00\x07"),
    (0x66, b"\x3c\x00\xcd\x67\x45\x45\x10\x00\x00\x00"),
    (0x67, b"\x00\x3c\x00\x00\x00\x01\x54\x10\x32\x98"),
    (0x74, b"\x10\x85\x80\x00\x00\x4e\x00"),
    (0x98, b"\x3e\x07"),
    (0x36, b"\x08"),
    (0x21, b""),
]

# Palette of the global constraints (index: RGB).
PALETTE = (
    (0, 0, 0),
    (51, 51, 51),
    (102, 102, 102),
    (153, 153, 153),
    (187, 187, 187),
    (255, 255, 255),
    (119, 255, 119),
    (255, 85, 85),
    (85, 85, 255),
    (255, 255, 85),
    (85, 255, 255),
    (255, 85, 255),
    (255, 165, 0),
    (0, 128, 0),
    (128, 0, 0),
    (0, 0, 128),
)

FULL_WINDOW = b"\x00\x00\x00\xef"


def color565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def wire(rgb):
    """The two bytes the panel expects for an RGB colour, high byte first."""
    return color565(*rgb).to_bytes(2, "big")


class LoggedPin(FakePin):
    """FakePin that logs every level change into a shared event list."""

    def __init__(self, name, log):
        super().__init__(name)
        self._log = log

    def value(self, val=None):
        if val is not None:
            self._log.append((self._id, int(val)))
        return super().value(val)

    def init(self, mode=FakePin.IN, pull=None, *, value=None):
        if value is not None:
            self._log.append((self._id, int(value)))
        super().init(mode, pull, value=value)


class Rig:
    """A GC9A01 on a FakeSPI, with pins and sleeps logged in order."""

    def __init__(self, device, rst=True):
        self.log = []
        self.dc = LoggedPin("dc", self.log)
        self.cs = LoggedPin("cs", self.log)
        self.rst = LoggedPin("rst", self.log) if rst else None
        self.spi = FakeSPI(1, dc=self.dc, cs=self.cs)
        write = self.spi.write

        def logged_write(buf):
            self.log.append(("write", len(buf)))
            write(buf)

        self.spi.write = logged_write
        self.dev = device.GC9A01(self.spi, self.dc, self.cs, self.rst)

    def frame(self):
        """The RGB565 bytes of the last RAMWR."""
        data = [d for cmd, d in self.spi.commands() if cmd == RAMWR]
        return data[-1]


@pytest.fixture
def device(monkeypatch):
    module, _ = load_driver_mock("gc9a01", None)
    sleeps = []
    monkeypatch.setattr(module, "sleep_ms", sleeps.append)
    module.sleeps = sleeps
    yield module
    cleanup_driver("gc9a01")


@pytest.fixture
def rig(device):
    r = Rig(device)

    def sleep(ms):
        r.log.append(("sleep", ms))

    device.sleep_ms = sleep
    return r


# ----- Constants -----


def test_palette_is_the_global_palette(device):
    const = importlib.import_module("gc9a01.const")
    assert const.PALETTE == PALETTE


def test_palette_rgb565_words_are_byte_swapped(device):
    const = importlib.import_module("gc9a01.const")
    assert len(const.PALETTE_RGB565) == 16
    for word, rgb in zip(const.PALETTE_RGB565, PALETTE):
        # Stored little-endian by framebuf, the word gives the panel bytes.
        assert word.to_bytes(2, "little") == wire(rgb)


def test_package_exports_the_driver(device):
    package = importlib.import_module("gc9a01")
    assert package.GC9A01 is device.GC9A01


# ----- Constructor -----


def test_constructor_touches_no_pin_or_bus(rig):
    assert rig.spi.writes == []
    assert rig.spi.inits == []
    assert rig.log == []
    assert len(rig.dev.buffer) == WIDTH * HEIGHT // 2
    assert rig.dev.width == WIDTH
    assert rig.dev.height == HEIGHT


# ----- init() -----


def test_init_resets_with_the_arduino_timing(rig):
    rig.dev.init()
    first_write = next(i for i, e in enumerate(rig.log) if e[0] == "write")
    reset = [e for e in rig.log[:first_write] if e[0] in ("rst", "sleep")]
    assert reset == [
        ("rst", 1),
        ("sleep", 10),
        ("rst", 0),
        ("sleep", 10),
        ("rst", 1),
        ("sleep", 120),
    ]


def test_init_without_reset_pin_sends_swreset(device):
    r = Rig(device, rst=False)
    r.dev.init()
    assert r.spi.commands()[0] == (SWRESET, b"")
    assert device.sleeps[0] == 120


def test_init_sends_the_arduino_sequence_then_clear_then_dispon(rig):
    rig.dev.init()
    cmds = rig.spi.commands()
    assert cmds[: len(ARDUINO_INIT)] == ARDUINO_INIT
    rest = cmds[len(ARDUINO_INIT) :]
    assert [c for c, _ in rest] == [SLPOUT, CASET, RASET, RAMWR, DISPON]
    assert rest[1] == (CASET, FULL_WINDOW)
    assert rest[2] == (RASET, FULL_WINDOW)
    assert rest[3][1] == bytes(FRAME_BYTES)


def test_init_waits_after_slpout_and_dispon(rig):
    rig.dev.init()
    sleeps = [e[1] for e in rig.log if e[0] == "sleep"]
    assert sleeps == [10, 10, 120, 120, 20]
    assert rig.log[-1] == ("sleep", 20)


def test_commands_have_dc_low_and_data_dc_high(rig):
    rig.dev.init()
    for dc, cs, data in rig.spi.writes:
        assert cs == 0
        if dc == 0:
            assert len(data) == 1
    cmd_bytes = [data[0] for dc, _cs, data in rig.spi.writes if dc == 0]
    assert cmd_bytes == [c for c, _ in rig.spi.commands()]


def test_init_clears_what_was_drawn_before(rig):
    rig.dev.fill(5)
    rig.dev.init()
    assert rig.frame() == bytes(FRAME_BYTES)


def test_spi_is_mode0_at_16mhz(rig):
    rig.dev.init()
    rig.dev.show()
    assert rig.spi.inits
    for kwargs in rig.spi.inits:
        assert kwargs == {"baudrate": 16_000_000, "polarity": 0, "phase": 0}


# ----- show() -----


def test_show_sends_window_then_the_frame(rig):
    rig.dev.show()
    cmds = rig.spi.commands()
    assert [c for c, _ in cmds] == [CASET, RASET, RAMWR]
    assert cmds[0][1] == FULL_WINDOW
    assert cmds[1][1] == FULL_WINDOW
    assert len(cmds[2][1]) == FRAME_BYTES


def test_show_white_and_red_high_byte_first(rig):
    rig.dev.pixel(0, 0, 5)  # WHITE
    rig.dev.pixel(1, 0, 7)  # RED (255, 85, 85)
    rig.dev.show()
    frame = rig.frame()
    assert frame[0:2] == b"\xff\xff"
    assert frame[2:4] == wire((255, 85, 85))
    assert frame[2:4] == b"\xfa\xaa"
    assert frame[4:] == bytes(FRAME_BYTES - 4)


def test_show_converts_every_palette_index(rig):
    rows = (0, 15, 16, 119, 239)  # first, both sides of a strip edge, middle, last
    for y in rows:
        for i in range(16):
            rig.dev.pixel(i * 15 + y % 7, y, i)
    rig.dev.show()
    frame = rig.frame()
    for y in rows:
        for i in range(16):
            offset = (y * WIDTH + i * 15 + y % 7) * 2
            assert frame[offset : offset + 2] == wire(PALETTE[i]), (y, i)
    for i in range(16):
        rig.dev.fill(i)
        rig.spi.clear()
        rig.dev.show()
        assert rig.frame() == wire(PALETTE[i]) * (WIDTH * HEIGHT), i


def test_show_last_pixel(rig):
    rig.dev.pixel(239, 239, 8)  # BLUE
    rig.dev.show()
    assert rig.frame()[-2:] == wire((85, 85, 255))
    assert rig.frame()[:-2] == bytes(FRAME_BYTES - 2)


def test_every_write_is_at_most_65535_bytes(rig):
    rig.dev.init()
    rig.dev.fill(3)
    rig.dev.show()
    assert max(len(data) for _dc, _cs, data in rig.spi.writes) <= 65535


def test_cs_is_held_low_for_the_whole_frame(rig):
    rig.dev.init()
    rig.spi.clear()
    rig.log.clear()
    rig.dev.show()
    assert len(rig.spi.inits) == 1
    assert all(cs == 0 for _dc, cs, _data in rig.spi.writes)
    cs_changes = [e for e in rig.log if e[0] == "cs"]
    assert cs_changes == [("cs", 0), ("cs", 1)]


def test_show_with_nothing_drawn_sends_zero_bytes(rig):
    rig.dev.show()
    assert rig.frame() == bytes(FRAME_BYTES)


def test_two_shows_send_the_init_sequence_once(rig):
    rig.dev.init()
    rig.dev.show()
    rig.dev.show()
    cmds = [c for c, _ in rig.spi.commands()]
    assert cmds.count(0xEB) == 2  # twice in kInitSequence, never again
    assert cmds.count(0x3A) == 1
    assert cmds.count(DISPON) == 1
    assert cmds.count(RAMWR) == 3  # clear in init(), then two show()


# ----- show() against the palette blit it replaced -----

# Panel size, then sizes with a short last strip (height not a multiple of
# STRIP_ROWS), fewer rows than a strip, and odd widths (the last byte of
# each GS4_HMSB row holds one pixel and a padding nibble).
GEOMETRIES = [(240, 240), (240, 37), (37, 23), (3, 40), (16, 5), (2, 17), (1, 1)]


class Guarded(bytearray):
    """A buffer that fails on any index outside it.

    Viper has no bounds check; Python would raise past the end but wrap a
    negative index silently, so both are refused here.
    """

    def __getitem__(self, i):
        assert isinstance(i, int), i
        assert 0 <= i < len(self), i
        return super().__getitem__(i)

    def __setitem__(self, i, v):
        assert isinstance(i, int), i
        assert 0 <= i < len(self), i
        super().__setitem__(i, v)


def make_device(device, width, height, seed=0):
    """A width x height driver on a FakeSPI, its frame filled with random bytes.

    Random bytes give every palette index in both nibbles, and a non-zero
    padding nibble at the end of the rows of an odd width.
    """
    dc = FakePin("dc")
    cs = FakePin("cs")
    spi = FakeSPI(1, dc=dc, cs=cs)
    dev = device.GC9A01(spi, dc, cs, None, width, height)
    dev.buffer[:] = random.Random(seed).randbytes(len(dev.buffer))
    return dev


def blit_strips(dev):
    """The frame writes of show() before viper: one palette blit per strip."""
    framebuf = sys.modules["framebuf"]
    const = importlib.import_module("gc9a01.const")
    width, height = dev.width, dev.height
    rows = min(const.STRIP_ROWS, height)
    strip = bytearray(width * 2 * rows)
    strip_fb = framebuf.FrameBuffer(strip, width, rows, framebuf.RGB565)
    palette = framebuf.FrameBuffer(bytearray(32), 16, 1, framebuf.RGB565)
    for i, word in enumerate(const.PALETTE_RGB565):
        palette.pixel(i, 0, word)
    source = framebuf.FrameBuffer(bytearray(dev.buffer), width, height, framebuf.GS4_HMSB)
    writes = []
    for y in range(0, height, rows):
        strip_fb.blit(source, 0, -y, -1, palette)
        left = min(rows, height - y)
        writes.append(bytes(strip[: left * width * 2]))
    return writes


def frame_writes(spi):
    """The data writes that follow the last RAMWR command."""
    ramwr = max(
        i for i, (dc, _cs, data) in enumerate(spi.writes) if dc == 0 and data == bytes([RAMWR])
    )
    return [data for _dc, _cs, data in spi.writes[ramwr + 1 :]]


@pytest.mark.parametrize(("width", "height"), GEOMETRIES)
def test_show_writes_the_strips_of_the_palette_blit(device, width, height):
    dev = make_device(device, width, height)
    expected = blit_strips(dev)
    dev.show()
    assert frame_writes(dev.spi) == expected


@pytest.mark.parametrize(("width", "height"), GEOMETRIES)
def test_show_stays_inside_the_frame_strip_and_palette(device, width, height):
    dev = make_device(device, width, height, seed=1)
    expected = blit_strips(dev)
    sizes = (len(dev.buffer), len(dev._strip), len(dev._palette))
    dev.buffer = Guarded(dev.buffer)
    dev._strip = Guarded(dev._strip)
    dev._palette = Guarded(dev._palette)
    dev.show()
    assert frame_writes(dev.spi) == expected
    assert (len(dev.buffer), len(dev._strip), len(dev._palette)) == sizes
    assert len(dev._strip) == width * 2 * min(16, height)
    assert len(dev._palette) == 32


def test_show_does_not_blit(device, monkeypatch):
    # The frame is converted by the viper function, not by FrameBuffer.blit.
    framebuf = sys.modules["framebuf"]

    def no_blit(*_args):
        raise AssertionError("show() used FrameBuffer.blit")

    for width, height in ((240, 20), (37, 3)):
        dev = make_device(device, width, height)
        expected = blit_strips(dev)
        monkeypatch.setattr(framebuf.FrameBuffer, "blit", no_blit)
        dev.show()
        monkeypatch.undo()
        assert frame_writes(dev.spi) == expected


# ----- Drawing -----


def test_drawing_off_screen_raises_nothing(device, rig):
    dev = rig.dev
    for x in (-10, 300):
        dev.pixel(x, 5, 5)
        assert dev.pixel(x, 5) is None
        dev.fill_rect(x, 5, 8, 8, 5)
        dev.rect(x, 5, 8, 8, 5)
        dev.line(x, 5, x, 50, 5)
        dev.text("Hi", x, 5, 5)
        dev.blit(dev.framebuf, x, 5)
    assert not any(dev.buffer)
    dev.show()
    assert len(rig.frame()) == FRAME_BYTES


def test_partly_visible_shapes_are_clipped(rig):
    dev = rig.dev
    dev.fill_rect(-10, 0, 20, 1, 5)
    dev.line(230, 10, 250, 10, 7)
    assert dev.pixel(9, 0) == 5
    assert dev.pixel(10, 0) == 0
    assert dev.pixel(239, 10) == 7
    dev.show()
    frame = rig.frame()
    assert frame[18:20] == b"\xff\xff"  # x = 9
    assert frame[20:22] == b"\x00\x00"  # x = 10


def test_pixel_reads_back_the_index(rig):
    rig.dev.pixel(3, 4, 9)
    assert rig.dev.pixel(3, 4) == 9


def test_rect_draws_an_outline(rig):
    rig.dev.rect(10, 10, 3, 3, 6)
    assert rig.dev.pixel(10, 10) == 6
    assert rig.dev.pixel(12, 12) == 6
    assert rig.dev.pixel(11, 11) == 0


def test_text_draws_the_framebuf_font(rig):
    rig.dev.text("A", 20, 30, 5)
    glyph = FONT_PETME128_8X8[(ord("A") - 32) * 8 : (ord("A") - 31) * 8]
    for x in range(8):
        for y in range(8):
            expected = 5 if glyph[x] >> y & 1 else 0
            assert rig.dev.pixel(20 + x, 30 + y) == expected, (x, y)


def test_blit_with_key(rig):
    import framebuf

    buf = bytearray(1)
    sprite = framebuf.FrameBuffer(buf, 2, 1, framebuf.GS4_HMSB)
    sprite.pixel(0, 0, 11)
    rig.dev.fill(2)
    rig.dev.blit(sprite, 50, 60, 0)
    assert rig.dev.pixel(50, 60) == 11
    assert rig.dev.pixel(51, 60) == 2


def test_blit_with_palette_maps_then_keys(rig):
    import framebuf

    rig.dev.fill(2)
    glyph = (memoryview(bytes([0b10100000]))[0:1], 3, 1, framebuf.MONO_HLSB)

    # Palette pixel 0 (high nibble) = 0, pixel 1 (low nibble) = 9, key 0:
    # set bits become 9, clear bits map to the key and are skipped.
    palette = framebuf.FrameBuffer(bytearray([(0 << 4) | 9]), 2, 1, framebuf.GS4_HMSB)
    rig.dev.blit(glyph, 50, 60, 0, palette)
    assert [rig.dev.pixel(x, 60) for x in range(50, 53)] == [9, 2, 9]

    # Colour 0 (BLACK) on set bits: the key moves to 1, so black is drawn.
    palette = framebuf.FrameBuffer(bytearray([(1 << 4) | 0]), 2, 1, framebuf.GS4_HMSB)
    rig.dev.blit(glyph, 50, 61, 1, palette)
    assert [rig.dev.pixel(x, 61) for x in range(50, 53)] == [0, 2, 0]


# ----- Power -----


def test_power_off_and_on(rig):
    rig.dev.power_off()
    assert [c for c, _ in rig.spi.commands()] == [DISPOFF, SLPIN]
    rig.spi.clear()
    rig.dev.power_on()
    assert [c for c, _ in rig.spi.commands()] == [SLPOUT, DISPON]
