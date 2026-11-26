from steami.board import Steami
from steami.const import (
    ADDRESS,
    E_NOT_ANSWERING,
    E_NOT_ON_THIS_BOARD,
    E_RELEASE_CONTRADICTED,
    Origin,
    Release,
    Status,
    route,
)

NAN = float("nan")

_ERRORS = {
    Status.OK: "",
    Status.NOT_STARTED: "not started",
    Status.NOT_ON_THIS_BOARD: "not on this board",
    Status.NOT_RESPONDING: "no answer",
}

# Where the release comes from, for E11. A release found by probing is not
# trusted: the chip that answered decided it.
_TRUSTED_ORIGINS = {
    Origin.FORCED: "forced by Steami.begin()",
    Origin.CONFIG: "read from the board config",
}


def _first(release, function):
    chips = route(release, function)
    return chips[0] if chips else None


class Handle(object):
    """Common part of the function classes, as Arduino SteamiHandle.

    Finds the chip that serves a function on this release, claims its shared
    driver, applies its calibration, and reports E10, E11 or E20 once.
    Creating a handle touches no hardware.

    For subclasses:

    - ``_NOUN`` names the function in messages ("temperature sensor").
    - ``_HINT`` ends the E10 message; ``_FALLBACK`` ends the E20 one and says
      what the reads return instead ("read() will return 0.").
    - ``_driver()`` returns the shared driver, calling ``begin()`` on first
      use, or None when the function is not available.
    - ``_read(absent, method, *args)`` calls a method of that driver and
      returns ``absent`` when there is no driver or the read fails.

    Messages are reported under the name of the subclass.
    """

    _NOUN = ""
    _HINT = "Check the board or try another one."
    _FALLBACK = ""

    def __init__(self, function):
        self._function = function
        self._chip = None
        self._status = Status.NOT_STARTED

    def begin(self):
        """Find the chip of the function. True when one answered.

        Idempotent: once tried, returns the same answer without bus traffic.
        """
        if self._status != Status.NOT_STARTED:
            return self._status == Status.OK
        release = Steami.release()
        candidates = route(release, self._function)
        if not candidates:
            if release == Release.UNKNOWN:
                self._status = Status.UNKNOWN_BOARD  # the board already reported E01
                return False
            self._status = Status.NOT_ON_THIS_BOARD
            self._report_not_on_this_board(release)
            return False
        for chip in candidates:
            if Steami.claim(chip) == Status.OK:
                Steami.calibrate(chip)
                self._chip = chip
                self._status = Status.OK
                return True
        self._status = Status.NOT_RESPONDING
        self._report_not_answering(release, candidates)
        return False

    def is_available(self):
        return self._status == Status.OK

    def status(self):
        """Return the state of the function (Status.*)."""
        return self._status

    def error(self):
        """Return "" when OK, "not started", "not on this board", "no answer"
        or "unknown board"."""
        return _ERRORS.get(self._status, "unknown board")

    def chip(self):
        """Return the name of the chip in use, "" when none."""
        return self._chip or ""

    def _driver(self):
        if self._status == Status.NOT_STARTED:
            self.begin()
        if self._status != Status.OK:
            return None
        return Steami._driver(self._chip)

    def _read(self, absent, method, *args):
        driver = self._driver()
        if driver is None:
            return absent
        try:
            return getattr(driver, method)(*args)
        except Exception:
            # Each driver raises its own error when the chip stops answering
            # (OSError, or a class of its own such as WSENHIDSCommunicationError).
            return absent

    def _report(self, code, detail):
        Steami.report(type(self).__name__, code, detail)

    def _report_not_on_this_board(self, release):
        other = Release.V1AB if release == Release.V1C else Release.V1C
        self._report(
            E_NOT_ON_THIS_BOARD,
            "this STeaMi is a {}, it has no {} ({} is on {} only). {}".format(
                Steami.release_name(),
                self._NOUN,
                _first(other, self._function),
                "V1a/V1b" if release == Release.V1C else "V1c",
                self._FALLBACK,
            ),
        )

    def _report_not_answering(self, release, candidates):
        first = candidates[0]
        # E11 only when the release decides which chip serves the function: a
        # chip that is on every release (distance, battery) never contradicts it.
        depends = _first(Release.V1C, self._function) != _first(Release.V1AB, self._function)
        origin = _TRUSTED_ORIGINS.get(Steami.origin()) if depends else None
        if origin is not None:
            self._report(
                E_RELEASE_CONTRADICTED,
                "this STeaMi is set as a {} ({}), but its {} {} (I2C 0x{:02X}) did not "
                "answer. Check Steami.begin() or the board config.".format(
                    Steami.release_name(), origin, first, self._NOUN, ADDRESS[first]
                ),
            )
        elif len(candidates) == 1:
            self._report(
                E_NOT_ANSWERING,
                "the {} {} (I2C 0x{:02X}) did not answer. {}".format(
                    first, self._NOUN, ADDRESS[first], self._HINT
                ),
            )
        else:
            self._report(
                E_NOT_ANSWERING,
                "no {} answered ({}). {}".format(self._NOUN, ", ".join(candidates), self._HINT),
            )
