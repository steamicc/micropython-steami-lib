"""List STeaMi driver modules and their source (frozen, filesystem, or missing)."""

drivers = [
    "apds9960",
    "bme280",
    "bq27441",
    "daplink_bridge",
    "daplink_flash",
    "gc9a01",
    "hts221",
    "im34dt05",
    "ism330dl",
    "lis2mdl",
    "mcp23009e",
    "ssd1327",
    "steami_config",
    "vl53l1x",
    "wsen_hids",
    "wsen_pads",
]

for d in drivers:
    try:
        mod = __import__(d)
        f = getattr(mod, "__file__", None)
        if f is None:
            print("  " + d + "  -> built-in")
        elif f.startswith("/"):
            print("  " + d + "  -> filesystem: " + f)
        else:
            print("  " + d + "  -> frozen")
    except ImportError:
        print("  " + d + "  -> NOT AVAILABLE")
