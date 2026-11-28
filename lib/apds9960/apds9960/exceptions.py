class APDS9960Error(OSError):
    """Base exception for the APDS9960 driver."""


class APDS9960InvalidDevId(APDS9960Error):
    def __init__(self, device_id, valid_ids):
        super().__init__(
            "Device id 0x{:02x} is not a valid one (valid: {})!".format(
                device_id,
                ", ".join(["0x{:02x}".format(i) for i in valid_ids]),
            ),
        )


class APDS9960InvalidMode(ValueError):
    def __init__(self, mode):
        super().__init__("Feature mode {} is invalid!".format(mode))
