"""STeaMi board detection and function classes.

Names are loaded on first use, so that a program only spends RAM on the
functions it imports: ``from steami import Temperature`` loads the board,
the constants, the shared handle and ``steami.temperature``, and nothing more.
"""

_SUBMODULES = {
    "Steami": "board",
    "Release": "const",
    "Chip": "const",
    "Function": "const",
    "Status": "const",
    "Origin": "const",
    "Vector": "const",
    "Temperature": "temperature",
    "Humidity": "humidity",
    "Pressure": "pressure",
    "Distance": "distance",
    "Battery": "battery",
    "Accelerometer": "accelerometer",
    "Gyroscope": "gyroscope",
    "Magnetometer": "magnetometer",
    "Compass": "compass",
    "Light": "light",
    "Color": "color",
    "Gesture": "gesture",
    "Buttons": "buttons",
}


def __getattr__(name):
    module = _SUBMODULES.get(name)
    if module is None:
        raise AttributeError(name)
    value = getattr(__import__("steami." + module, None, None, (name,)), name)
    globals()[name] = value
    return value
