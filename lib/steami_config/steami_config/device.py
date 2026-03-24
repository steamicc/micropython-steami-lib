import json

# Map sensor class names to short JSON keys to save space.
_SENSOR_KEYS = {
    "hts221": "hts",
    "lis2mdl": "mag",
    "ism330dl": "ism",
    "wsen_hids": "hid",
    "wsen_pads": "pad",
}

# Reverse map: short key -> sensor name.
_KEY_SENSORS = {v: k for k, v in _SENSOR_KEYS.items()}


class SteamiConfig(object):
    """Persistent configuration stored in the DAPLink F103 config zone.

    Data is serialised as compact JSON and written via
    ``DaplinkFlash.write_config()`` / ``read_config()``.

    Args:
        flash: a ``DaplinkFlash`` instance.
    """

    def __init__(self, flash):
        self._flash = flash
        self._data = {}

    # --------------------------------------------------
    # Persistence
    # --------------------------------------------------

    def load(self):
        """Load configuration from the config zone.

        Falls back to empty config if the zone contains invalid JSON.
        """
        raw = self._flash.read_config()
        if raw:
            try:
                self._data = json.loads(raw)
            except (ValueError, TypeError):
                self._data = {}
        else:
            self._data = {}

    def save(self):
        """Save configuration to the config zone."""
        self._flash.clear_config()
        self._flash.write_config(json.dumps(self._data, separators=(",", ":")))

    # --------------------------------------------------
    # Board info
    # --------------------------------------------------

    @property
    def board_revision(self):
        """Board hardware revision number, or None."""
        return self._data.get("rev")

    @board_revision.setter
    def board_revision(self, value):
        if value is None:
            self._data.pop("rev", None)
        else:
            self._data["rev"] = int(value)

    @property
    def board_name(self):
        """Board name string, or None."""
        return self._data.get("name")

    @board_name.setter
    def board_name(self, value):
        if value is None:
            self._data.pop("name", None)
        else:
            self._data["name"] = str(value)

    # --------------------------------------------------
    # Temperature calibration
    # --------------------------------------------------

    def set_temperature_calibration(self, sensor, gain=1.0, offset=0.0):
        """Store temperature calibration for a sensor.

        Args:
            sensor: sensor name (e.g. ``"hts221"``, ``"wsen_pads"``).
            gain: multiplicative gain factor.
            offset: additive offset in degrees Celsius.
        """
        key = _SENSOR_KEYS.get(sensor)
        if key is None:
            raise ValueError("unknown sensor: {}".format(sensor))
        tc = self._data.get("tc")
        if tc is None:
            tc = {}
            self._data["tc"] = tc
        tc[key] = {"g": gain, "o": offset}

    def get_temperature_calibration(self, sensor):
        """Return temperature calibration for a sensor.

        Returns:
            dict with ``"gain"`` and ``"offset"`` keys, or None.
        """
        key = _SENSOR_KEYS.get(sensor)
        if key is None:
            raise ValueError("unknown sensor: {}".format(sensor))
        tc = self._data.get("tc")
        if tc is None:
            return None
        entry = tc.get(key)
        if entry is None:
            return None
        return {"gain": entry["g"], "offset": entry["o"]}

    def apply_temperature_calibration(self, sensor_instance):
        """Apply stored calibration to a sensor instance.

        The sensor class name is used to look up calibration data.
        The instance must have ``_temp_gain`` and ``_temp_offset``
        attributes (all STeaMi temperature sensors do).

        Args:
            sensor_instance: a driver instance (e.g. ``HTS221``).
        """
        class_name = type(sensor_instance).__name__.lower()
        if class_name not in _SENSOR_KEYS:
            return
        cal = self.get_temperature_calibration(class_name)
        if cal is None:
            return
        sensor_instance._temp_gain = cal["gain"]
        sensor_instance._temp_offset = cal["offset"]
