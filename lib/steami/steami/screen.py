from steami_screen import Screen as _Screen

from steami.board import Steami
from steami.const import E_NO_MEMORY, E_SCREEN_UNKNOWN_BOARD, Chip, Function, Status
from steami.handle import Handle

_UNKNOWN_BOARD = (
    "cannot tell if this board is a V1a/V1b or a V1c. "
    'Call Steami.begin("V1c") (or "V1b") at the start of the program.'
)
_NO_MEMORY = (
    "not enough RAM for the screen ({} bytes in one block). "
    "Call begin() on the Screen first in the program."
)


def _nothing(*args):
    pass


class _Off(object):
    """Stands for the display when there is none: every call does nothing."""

    width = height = 128  # the default size of steami_screen

    def __getattr__(self, name):
        return _nothing


class Screen(Handle, _Screen):
    """The board screen: SSD1327 on V1a/V1b, GC9A01 on V1c.

    Offers the whole steami_screen.Screen drawing API. Creating it touches
    no hardware; begin(), or the first use, starts the shared display
    (Steami.display()). Without one (unknown board, E30, or not enough RAM,
    E31), drawing calls do nothing; width and height are then the panel's
    size (E31) or 128 (E30).
    """

    def __init__(self):
        super().__init__(Function.SCREEN)

    def __getattr__(self, name):
        # _d, width and height are set by begin(): the first use starts the screen.
        if name in ("_d", "width", "height"):
            self.begin()
            return getattr(self, name)
        raise AttributeError(name)

    def begin(self):
        """Start the screen. True when it is ready. Idempotent."""
        if self._status == Status.NOT_STARTED:
            d = Steami.display()
            self._chip = Steami._display_chip
            status = Status.OK
            if d is None:
                d = _Off()
                if self._chip:
                    status = Status.NO_MEMORY
                    d.width = d.height = 240 if self._chip == Chip.GC9A01 else 128
                    self._report(E_NO_MEMORY, _NO_MEMORY.format(d.width * d.height // 2))
                else:
                    status = Status.UNKNOWN_BOARD
                    self._report(E_SCREEN_UNKNOWN_BOARD, _UNKNOWN_BOARD)
            self._d = d
            self.width = d.width
            self.height = d.height
            self._status = status
        return self._status == Status.OK

    def error(self):
        """Return "" when OK, "not started", "unknown board" or "no memory"."""
        return "" if self._status == Status.OK else self._status
