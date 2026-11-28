"""Fake Pin for testing drivers without hardware."""


class FakePin:
    """Simulates a MicroPython Pin."""

    IN = 0
    OUT = 1
    PULL_UP = 1
    PULL_DOWN = 2
    IRQ_FALLING = 1
    IRQ_RISING = 2

    def __init__(self, pin_id, mode=IN, pull=None):
        self._id = pin_id
        self._mode = mode
        self._pull = pull
        self._value = 0
        self._irq = None  # (handler, trigger, hard) set by irq()

    def value(self, val=None):
        if val is None:
            return self._value
        self._value = val

    def init(self, mode=IN, pull=None, *, value=None):
        self._mode = mode
        self._pull = pull
        if value is not None:
            self._value = value

    def irq(self, handler=None, trigger=IRQ_FALLING | IRQ_RISING, *, hard=False):
        self._irq = (handler, trigger, hard)

    def drive(self, level):
        """Set the input level and run the IRQ handler on a matching edge, as the board does."""
        old = self._value
        self._value = level
        if self._irq is None or self._irq[0] is None or level == old:
            return
        handler, trigger, _ = self._irq
        if trigger & (self.IRQ_RISING if level else self.IRQ_FALLING):
            handler(self)
