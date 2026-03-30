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
    ``DaplinkBridge.write_config()`` / ``read_config()``.

    Args:
        bridge: a ``DaplinkBridge`` instance.
    """

    def __init__(self, bridge):
        self._bridge = bridge
        self._data = {}

    # --------------------------------------------------
    # Persistence
    # --------------------------------------------------

    def load(self):
        """Load configuration from the config zone.

        Falls back to empty config if the zone contains invalid JSON.
        """
        raw = self._bridge.read_config()
        if raw:
            try:
                self._data = json.loads(raw)
            except (ValueError, TypeError):
                self._data = {}
        else:
            self._data = {}

    def save(self):
        """Save configuration to the config zone."""
        self._bridge.clear_config()
        self._bridge.write_config(json.dumps(self._data, separators=(",", ":")))

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

    # --------------------------------------------------
    # Magnetometer calibration
    # --------------------------------------------------

    def set_magnetometer_calibration(
        self,
        hard_iron_x=0.0,
        hard_iron_y=0.0,
        hard_iron_z=0.0,
        soft_iron_x=1.0,
        soft_iron_y=1.0,
        soft_iron_z=1.0,
    ):
        """Store magnetometer hard-iron and soft-iron calibration.

        Args:
            hard_iron_x: X-axis hard-iron offset.
            hard_iron_y: Y-axis hard-iron offset.
            hard_iron_z: Z-axis hard-iron offset.
            soft_iron_x: X-axis soft-iron scale factor.
            soft_iron_y: Y-axis soft-iron scale factor.
            soft_iron_z: Z-axis soft-iron scale factor.
        """
        self._data["cm"] = {
            "hx": hard_iron_x,
            "hy": hard_iron_y,
            "hz": hard_iron_z,
            "sx": soft_iron_x,
            "sy": soft_iron_y,
            "sz": soft_iron_z,
        }

    def get_magnetometer_calibration(self):
        """Return magnetometer calibration data.

        Returns:
            dict with hard_iron_x/y/z and soft_iron_x/y/z keys, or None.
        """
        cm = self._data.get("cm")
        if cm is None:
            return None
        return {
            "hard_iron_x": cm.get("hx", 0.0),
            "hard_iron_y": cm.get("hy", 0.0),
            "hard_iron_z": cm.get("hz", 0.0),
            "soft_iron_x": cm.get("sx", 1.0),
            "soft_iron_y": cm.get("sy", 1.0),
            "soft_iron_z": cm.get("sz", 1.0),
        }

    def apply_magnetometer_calibration(self, lis2mdl_instance):
        """Apply stored magnetometer calibration to a LIS2MDL instance.

        The instance must have x_off/y_off/z_off and x_scale/y_scale/z_scale
        attributes.  Only applies to LIS2MDL instances.

        Args:
            lis2mdl_instance: a LIS2MDL driver instance.
        """
        if type(lis2mdl_instance).__name__.lower() != "lis2mdl":
            return
        cal = self.get_magnetometer_calibration()
        if cal is None:
            return
        lis2mdl_instance.x_off = cal["hard_iron_x"]
        lis2mdl_instance.y_off = cal["hard_iron_y"]
        lis2mdl_instance.z_off = cal["hard_iron_z"]
        lis2mdl_instance.x_scale = cal["soft_iron_x"]
        lis2mdl_instance.y_scale = cal["soft_iron_y"]
        lis2mdl_instance.z_scale = cal["soft_iron_z"]

    # --------------------------------------------------
    # Accelerometer calibration
    # --------------------------------------------------

    def set_accelerometer_calibration(self, ox=0.0, oy=0.0, oz=0.0):
        """Store accelerometer bias offsets (in g).

        Args:
            ox: X-axis offset
            oy: Y-axis offset
            oz: Z-axis offset
        """
        self._data["cal_accel"] = {
            "ox": float(ox),
            "oy": float(oy),
            "oz": float(oz),
        }


    def get_accelerometer_calibration(self):
        """Return accelerometer calibration offsets.

        Returns:
            dict with ox, oy, oz or None
        """
        cal = self._data.get("cal_accel")
        if cal is None:
            return None

        return {
            "ox": cal.get("ox", 0.0),
            "oy": cal.get("oy", 0.0),
            "oz": cal.get("oz", 0.0),
        }


    def apply_accelerometer_calibration(self, ism330dl_instance):
        """Apply stored calibration to ISM330DL instance.

        The instance must support offset attributes (user-defined).

        Args:
            ism330dl_instance: ISM330DL driver instance
        """
        if type(ism330dl_instance).__name__.lower() != "ism330dl":
            return

        cal = self.get_accelerometer_calibration()
        if cal is None:
            return

        # the driver does NOT have native offset support, so we add attributes dynamically
        ism330dl_instance._accel_offset_x = cal["ox"]
        ism330dl_instance._accel_offset_y = cal["oy"]
        ism330dl_instance._accel_offset_z = cal["oz"]
