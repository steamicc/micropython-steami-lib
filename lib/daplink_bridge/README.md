# DAPLink Bridge MicroPython Driver

Low-level I2C bridge driver for the **STM32F103 DAPLink interface** on the STeaMi board.

This driver handles all direct I2C communication with the bridge: device identification, status/error registers, busy polling, and persistent config zone access (1 KB internal flash).

# I2C Address

Default 7-bit I2C address: `0x3B`

# Basic Usage

```python
from machine import I2C
from daplink_bridge import DaplinkBridge

i2c = I2C(1)
bridge = DaplinkBridge(i2c)

print("WHO_AM_I:", hex(bridge.device_id()))
print("Busy:", bridge.busy())
```

# API

## Initialization

```python
bridge = DaplinkBridge(i2c, address=0x3B)
```

Create a new DAPLink bridge instance.

Parameters:

* `i2c`: initialized MicroPython `I2C` bus
* `address`: I2C address of the bridge, default is `0x3B`

## Device identification

### `device_id()`

```python
bridge.device_id()
```

Read the `WHO_AM_I` register. Expected value: `0x4C`.

## Status

### `busy()`

```python
bridge.busy()
```

Returns `True` if the bridge is currently busy, otherwise `False`.

## Config zone

The config zone is a **1 KB persistent storage area** in the STM32F103 internal flash. It is separate from the external flash file storage and survives `clear_flash()` operations.

### `clear_config()`

```python
bridge.clear_config()
```

Erase the entire config zone. Raises `OSError` if the operation fails.

### `write_config(data, offset=0)`

```python
bridge.write_config("board_rev=3", offset=0)
bridge.write_config(b"\x01\x02\x03", offset=100)
```

Write data into the config zone at the given byte offset.

Parameters:

* `data`: `str` or `bytes`
* `offset`: byte offset in the range `0` to `1023`

Notes:

* existing data outside the written range is preserved
* raises `ValueError` if the write would go out of bounds
* raises `OSError` if the bridge reports a write error

### `read_config()`

```python
cfg = bridge.read_config()
```

Read back config zone content.

Returns:

* `bytes` up to the first `0xFF`
* `b""` if the config zone is empty

# Architecture

```
steami_config  ──┐
                 ├──→  daplink_bridge  ──→  I2C (STM32F103)
daplink_flash  ──┘
```

* [`daplink_flash`](../daplink_flash/README.md) — high-level flash file operations
* [`steami_config`](../steami_config/README.md) — persistent board configuration (JSON)

# Notes

* The bridge uses a `WHO_AM_I` value of `0x4C`.
* The config zone (1 KB) is separate from the external flash file area.
* All I2C operations go through private helpers (`_read_reg`, `_write_reg`, `_writeto`, `_readfrom`).
