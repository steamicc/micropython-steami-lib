from steami.const import Function
from steami.handle import NAN, Handle


class Battery(Handle):
    """Battery gauge: BQ27441, on every release. It answers only with a battery plugged in.

    Creating it touches no hardware.
    """

    _NOUN = "battery gauge"
    _HINT = "Plug in a battery, then reset the board."
    _FALLBACK = "percent() will return 0."

    def __init__(self):
        super().__init__(Function.BATTERY)

    def percent(self):
        """Remaining charge in percent; 0 when unavailable. Calls begin() on first use."""
        return self._read(0, "state_of_charge")

    def voltage(self):
        """Battery voltage in volts; nan when unavailable."""
        mv = self._read(0, "voltage_mv")
        return mv / 1000.0 if mv > 0 else NAN

    def current(self):
        """Average current in mA, negative when discharging; 0 when unavailable."""
        return self._read(0, "current_average")

    def is_charging(self):
        """True when current() is positive."""
        return self.current() > 0
