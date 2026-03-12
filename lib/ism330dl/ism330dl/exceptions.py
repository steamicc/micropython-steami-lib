class ISM330DLError(Exception):
    """Base exception for ISM330DL driver."""


class ISM330DLNotFound(ISM330DLError):
    """Raised when the sensor is not detected."""


class ISM330DLConfigError(ISM330DLError):
    """Raised when configuration is invalid."""


class ISM330DLIOError(ISM330DLError):
    """Raised when an I2C communication error occurs."""
