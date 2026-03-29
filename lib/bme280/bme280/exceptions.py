class BME280Error(Exception):
    """Base exception for BME280 driver."""


class BME280NotFound(BME280Error):
    """Device not found on I2C bus."""


class BME280InvalidDevice(BME280Error):
    """Device ID mismatch."""
