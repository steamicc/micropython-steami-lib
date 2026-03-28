class APDS9960InvalidDevId(ValueError):
    def __init__(self, device_id, valid_ids):
        Exception.__init__(
            self,
            "Device id 0x{} is not a valid one (valid: {})!".format(
                format(device_id, "02x"),
                ", ".join(["0x{}".format(format(i, "02x")) for i in valid_ids]),
            ),
        )


class APDS9960InvalidMode(ValueError):
    def __init__(self, mode):
        Exception.__init__(self, "Feature mode {} is invalid!".format(mode))
