from time import ticks_diff, ticks_ms

from steami.const import Function, Status
from steami.handle import Handle

# Names of the driver directions, in the order of its APDS9960_DIR_* constants.
_DIRECTIONS = ("NONE", "LEFT", "RIGHT", "UP", "DOWN", "NEAR", "FAR")


def _gesture(driver, timeout_ms):
    start = ticks_ms()
    index = driver.gesture()
    # A pass can end on noise while the chip still holds data: go on, within the timeout.
    while (
        index == 0 and ticks_diff(ticks_ms(), start) < timeout_ms and driver.is_gesture_available()
    ):
        index = driver.gesture()
    return _DIRECTIONS[index] if 0 <= index < len(_DIRECTIONS) else Gesture.NONE


class Gesture(Handle):
    """Hand gestures: APDS-9960, on V1a and V1b only. A V1c reports E20.

    Shares the chip with Light and Color. begin() turns the gesture engine on
    without turning the light engine off; while a hand is over the sensor, the
    light and colour readings pause. Creating it touches no hardware.
    """

    NONE = "NONE"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    UP = "UP"
    DOWN = "DOWN"
    NEAR = "NEAR"
    FAR = "FAR"

    _NOUN = "gesture sensor"
    _FALLBACK = "read() will return NONE."

    def __init__(self):
        super().__init__(Function.GESTURE)

    def begin(self):
        """Find the chip and turn its gesture engine on. True when it answered."""
        if self._status != Status.NOT_STARTED:
            return super().begin()
        ok = super().begin()
        if ok:
            self._read(None, "enable_gesture_sensor", False)
        return ok

    def read(self, timeout_ms=0):
        """The gesture in progress (Gesture.UP, ...).

        Stops retrying after timeout_ms; one decode can take longer while a
        hand stays over the sensor.

        Gesture.NONE when the sensor has not seen a gesture (it does not wait
        for one to start) or when unavailable. Call it on every loop turn; with
        0 it decodes what the chip already holds and can cut a gesture short.
        Calls begin() on first use.
        """
        return self._read(Gesture.NONE, _gesture, timeout_ms)

    @staticmethod
    def name(direction):
        """The text of a direction: "NONE", "LEFT", "RIGHT", "UP", "DOWN", "NEAR" or "FAR"."""
        return direction if direction in _DIRECTIONS else Gesture.NONE
