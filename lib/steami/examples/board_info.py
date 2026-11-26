"""Print the detected board release, where the answer comes from, and the chips.

The release is found from three sources, in this order:
  1. a forced value: Steami.begin("V1c") (or "V1a", "V1b");
  2. the board revision stored in the DAPLink config zone, when there is one;
  3. an I2C probe: BME280 means V1c, WSEN-HIDS, WSEN-PADS or APDS-9960 means V1a/V1b.

print_info() lists the chips of the release with OK, "not responding" or
"not tried". "Not tried" means no function used that chip yet, so this program
first claims every chip of the release: each line then shows whether the chip
really answers.
"""

from steami import Chip, Steami

# To force a V1c, uncomment the next line:
# Steami.begin("V1c")

Steami.begin()
for chip in (
    Chip.BME280,
    Chip.WSEN_HIDS,
    Chip.WSEN_PADS,
    Chip.APDS9960,
    Chip.VL53L1X,
    Chip.ISM330DL,
    Chip.LIS2MDL,
    Chip.BQ27441,
    Chip.MCP23009E,
):
    Steami.claim(chip)
Steami.print_info()
