from daplink_bridge import DaplinkBridge
from machine import I2C
from steami_config import SteamiConfig

# --- Hardware init ---
i2c = I2C(1)
bridge = DaplinkBridge(i2c)

config = SteamiConfig(bridge)
config.load()

# --- Boot counter logic ---
config.increment_boot_count()

# Save updated value
config.save()

# Read and display
count = config.get_boot_count()

print("Boot count:", count)
