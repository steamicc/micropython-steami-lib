class WSENHIDSError(Exception):
    """Base exception for the WSEN-HIDS driver."""


class WSENHIDSCommunicationError(WSENHIDSError):
    """Raised when an I2C communication error occurs."""


class WSENHIDSDeviceIDError(WSENHIDSError):
    """Raised when the device ID does not match the expected value."""


class WSENHIDSTimeoutError(WSENHIDSError):
    """Raised when a conversion does not complete before timeout."""
