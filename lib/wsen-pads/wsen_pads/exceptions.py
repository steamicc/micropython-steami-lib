class WSENPADSError(Exception):
    """Base exception for all WSEN-PADS driver errors."""


class WSENPADSDeviceNotFound(WSENPADSError):
    """Raised when the device does not respond on the I2C bus."""


class WSENPADSInvalidDevice(WSENPADSError):
    """Raised when the detected device ID does not match WSEN-PADS."""


class WSENPADSTimeout(WSENPADSError):
    """Raised when a blocking operation exceeds the expected timeout."""
    