"""Mock tests of the steami_screen gauge: allocation and pixel identity (#456).

On the board gauge() allocated about 36 KB per call (0.27-0.56 s per draw):
each row of each ring made two floats (math.sqrt) and three span tuples,
and each span went through Screen._fill_rect, the adapter and a palette
lookup. The arc now converts its colour once, draws its spans straight on
the driver's fill_rect and uses integer square roots.

Allocation is measured with a model of the MicroPython heap, since CPython
frees these objects at once (tracemalloc sees no peak): every executed
BUILD_TUPLE, BUILD_LIST, BUILD_MAP, BUILD_SET or MAKE_FUNCTION in a
steami_screen frame, plus every math.sqrt call (a boxed float on the
STM32), counts as one allocation.

Pixel identity: the frames of the new arc are compared byte for byte with
those of the previous arc, kept below as old_draw_arc().
"""

import dis
import math
import os
import sys

import pytest

from tests.fake_machine import FakePin, FakeSPI
from tests.runner.executor import cleanup_driver, load_driver_mock

ALLOC_OPS = {"BUILD_TUPLE", "BUILD_LIST", "BUILD_MAP", "BUILD_SET", "MAKE_FUNCTION"}
DARK, LIGHT = 2, 4


@pytest.fixture
def mods():
    load_driver_mock("steami_screen", None)
    module, _ = load_driver_mock("gc9a01", None)
    yield sys.modules["steami_screen"], module
    cleanup_driver("gc9a01")
    cleanup_driver("steami_screen")


@pytest.fixture
def panel(mods):
    """new(size) -> (Screen, raw driver) on a fresh black frame."""
    steami_screen, driver = mods

    def new(size=240):
        raw = driver.GC9A01(FakeSPI(1), FakePin("dc"), FakePin("cs"), width=size, height=size)
        return steami_screen.Screen(steami_screen.GC9A01Display(raw)), raw

    return new


def old_draw_arc(self, cx, cy, r, start_deg, sweep_deg, color, width=3):
    """The arc of v0.31.2 (before #456), the pixel reference."""
    _ray = sys.modules["steami_screen.device"]._ray
    if hasattr(self._d, "draw_arc"):
        self._d.draw_arc(cx, cy, r, start_deg, sweep_deg, color, width)
        return
    if sweep_deg <= 0:
        return
    half = width // 2
    ro, ri = r + half, max(0, r - half)
    secs = ()
    if sweep_deg < 360:
        m = start_deg + min(sweep_deg, 180)
        secs = (_ray(start_deg) + _ray(m),)
        if sweep_deg > 180:
            secs += (_ray(m) + _ray(start_deg + sweep_deg),)
    o2, i2 = (2 * ro + 1) ** 2, (2 * ri - 1) ** 2
    fr = self._fill_rect
    for dy in range(max(-ro, -cy), min(ro, self.height - 1 - cy) + 1):
        d4 = 4 * dy * dy
        xo = int(math.sqrt((o2 - d4) // 4))
        xi = 0
        q = (i2 - d4 + 3) // 4
        if ri and q > 0:
            xi = int(math.sqrt(q))
            xi += xi * xi < q
        if xi > xo:
            continue
        y = cy + dy
        for lo, hi in ((-xo, -xi), (xi, xo)) if xi else ((-xo, xo),):
            if not secs:
                fr(cx + lo, y, hi - lo + 1, 1, color)
                continue
            for sx, sy, ex, ey in secs:
                a, b = lo, hi
                c = sx * dy
                if sy > 0:
                    b = min(b, c // sy)
                elif sy < 0:
                    a = max(a, -(c // -sy))
                elif c < 0:
                    continue
                c = ex * dy
                if ey > 0:
                    a = max(a, -(-c // ey))
                elif ey < 0:
                    b = min(b, c // ey)
                elif c > 0:
                    continue
                if a <= b:
                    fr(cx + a, y, b - a + 1, 1, color)


def frames(mods, panel, size, draw):
    """(new frame, old frame) of draw(screen) on a size px panel."""
    steami_screen, _ = mods
    s, raw = panel(size)
    draw(s)
    new = bytes(raw.buffer)
    cls = steami_screen.Screen
    keep = cls._draw_arc
    cls._draw_arc = old_draw_arc
    try:
        s, raw = panel(size)
        draw(s)
        old = bytes(raw.buffer)
    finally:
        cls._draw_arc = keep
    return new, old


def board_allocs(fn, monkeypatch):
    """(allocations, palette lookups) of fn() in the MicroPython heap model.

    Only the frames of the steami_screen package are traced. fn runs twice
    and the second run is counted, so fn must draw the same thing again.
    """
    n = {"alloc": 0, "lookup": 0}
    sqrt = math.sqrt

    def counted_sqrt(v):
        n["alloc"] += 1
        return sqrt(v)

    monkeypatch.setattr(math, "sqrt", counted_sqrt)
    package = os.path.dirname(sys.modules["steami_screen"].__file__)

    def tracer(frame, event, arg):
        code = frame.f_code
        if not code.co_filename.startswith(package):
            return None
        if event == "call":
            n["lookup"] += code.co_name in ("rgb_to_index", "rgb_to_gray4")
            frame.f_trace_opcodes = True
        elif event == "opcode":
            n["alloc"] += dis.opname[code.co_code[frame.f_lasti]] in ALLOC_OPS
        return tracer

    old = sys.gettrace()
    sys.settrace(tracer)
    try:
        # A first run instruments the code objects: on Python 3.12+ the first
        # traced call of a function can miss some of its opcode events.
        fn()
        n["alloc"] = n["lookup"] = 0
        fn()
    finally:
        sys.settrace(old)
    return n["alloc"], n["lookup"]


# ----- Pixel identity with the previous arc -----


GAUGES = (
    lambda s: s.gauge(0),
    lambda s: s.gauge(0.4),
    lambda s: s.gauge(1),
    lambda s: s.gauge(50),
    lambda s: s.gauge(66.6, color=(255, 85, 85)),
    lambda s: s.gauge(99.9, color=5),
    lambda s: s.gauge(100),
    lambda s: s.gauge(150),
    lambda s: s.gauge(-5, min_val=-10, max_val=40),
    lambda s: s.gauge(25, arc_width=8),
    lambda s: s.gauge(30, arc_width=1),
    lambda s: s.gauge(70, arc_width=31),
    lambda s: s.gauge(1500, min_val=0, max_val=3000),
    lambda s: s.gauge(3, min_val=3, max_val=3),
)


@pytest.mark.parametrize("size", (240, 128))
@pytest.mark.parametrize("i", range(len(GAUGES)))
def test_mock_gauge_frame_is_byte_identical_to_the_old_arc(mods, panel, size, i):
    new, old = frames(mods, panel, size, GAUGES[i])
    assert new == old


ARCS = (
    # (cx, cy, r, start, sweep, width) in fractions of the size for cx, cy, r.
    (0.5, 0.5, 0.45, 135, 270, 13),
    (0.5, 0.5, 0.3, 0, 360, 9),
    (0.5, 0.5, 0.3, 90, 400, 4),
    (0.5, 0.5, 0.2, 45, 1, 7),
    (0.5, 0.5, 0.2, 180, 180, 7),
    (0.5, 0.5, 0.2, 180, 181, 6),
    (0.5, 0.5, 0.35, 300, 359, 15),
    (0.5, 0.5, 0.35, 270, 90, 2),
    (0.5, 0.5, 0.0, 0, 360, 5),
    (0.5, 0.5, 0.01, 10, 200, 1),
    (0.05, 0.03, 0.4, 135, 270, 11),
    (0.95, 0.98, 0.4, 0, 300, 11),
    (0.2, 0.9, 0.6, 225, 120, 21),
    (0.5, 0.5, 0.7, 0, 360, 31),
    (0.5, 0.5, 0.25, 135, 0, 9),
    (0.5, 0.5, 0.25, 135, -10, 9),
)


@pytest.mark.parametrize("size", (240, 128))
@pytest.mark.parametrize("cx,cy,r,start,sweep,width", ARCS)
def test_mock_arc_frame_is_byte_identical_to_the_old_arc(
    mods, panel, size, cx, cy, r, start, sweep, width
):
    def draw(s):
        s._draw_arc(
            int(cx * size), int(cy * size), int(r * size), start, sweep, (255, 255, 255), width
        )

    new, old = frames(mods, panel, size, draw)
    assert new == old


# ----- Allocation -----


def test_mock_arc_allocations_do_not_grow_with_the_rows(panel, monkeypatch):
    # No float, tuple or list per row or per span: a 7-row and a 227-row arc
    # allocate the same 7 objects (4 rays and 2 sector tuples, the
    # native_fill() pair) and look the colour up once. The old arc made 1089
    # allocations and 384 lookups (one per span) for the 227-row one.
    counts = []
    for r, w in ((2, 3), (107, 13)):
        s, _ = panel()
        arc = (120, 120, r, 135, 270, (187, 187, 187), w)
        counts.append(board_allocs(lambda s=s, arc=arc: s._draw_arc(*arc), monkeypatch))
    assert counts[0] == counts[1]
    assert counts[1] == (7, 1)


@pytest.mark.parametrize("size", (240, 128))
def test_mock_gauge_allocation_is_bounded(panel, monkeypatch, size):
    # gauge(50): the old one made 1539 allocations at 240 (852 at 128) and
    # 581 palette lookups (326), one per span. Now 45 (15), most of them for
    # the two labels, and 4 lookups: one per arc, one per label.
    s, _ = panel(size)
    allocs, lookups = board_allocs(lambda: s.gauge(50), monkeypatch)
    assert allocs <= 60
    assert lookups <= 4


# ----- Small values -----


def test_mock_gauge_below_one_degree_shows_an_empty_gauge(panel):
    # As the Arduino gauge: the fill sweeps int(270 * ratio) degrees, so a
    # value with 0 < ratio < 1/270 draws no fill (0.3 of 100: 0.81 degree).
    s, raw = panel()
    s.gauge(0.3)
    assert LIGHT not in {b >> 4 for b in raw.buffer} | {b & 15 for b in raw.buffer}
    s, raw = panel()
    s.gauge(0.4)  # 1.08 degree: a 1 degree fill
    assert LIGHT in {b >> 4 for b in raw.buffer} | {b & 15 for b in raw.buffer}
