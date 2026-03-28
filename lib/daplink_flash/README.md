# DAPLink Flash MicroPython Driver

High-level flash file operations for the STeaMi board, built on top of the [`daplink_bridge`](../daplink_bridge/) module.

This driver provides 8.3 filename management, data writing, and sector-based reading for the external **W25Q64JV SPI flash** connected via the STM32F103 DAPLink bridge.

# Dependencies

* `daplink_bridge` — low-level I2C bridge communication

# Basic Usage

```python
from machine import I2C
from daplink_bridge import DaplinkBridge
from daplink_flash import DaplinkFlash

i2c = I2C(1)
bridge = DaplinkBridge(i2c)
flash = DaplinkFlash(bridge)

flash.set_filename("LOG", "TXT")
flash.clear_flash()

flash.write_line("Hello from STeaMi!")
flash.write_line("DAPLink flash test")

content = flash.read()
print(content.decode())
```

# API

## Initialization

```python
flash = DaplinkFlash(bridge)
```

Create a new DAPLink flash driver instance.

Parameters:

* `bridge`: a `DaplinkBridge` instance

## Filename management

### `set_filename(name, ext)`

```python
flash.set_filename("DATA", "CSV")
```

Set the current file name using the DOS 8.3 format.

Parameters:

* `name`: file name, up to 8 characters
* `ext`: extension, up to 3 characters

The driver automatically uppercases and pads the values as needed.

### `get_filename()`

```python
flash.get_filename()
```

Returns the current file name as:

```python
(name, ext)
```

## Flash operations

### `clear_flash()`

```python
flash.clear_flash()
```

Erase the entire external flash memory.

This removes the stored file content. The config zone (managed by `DaplinkBridge`) is not affected.

### `write(data)`

```python
flash.write("hello")
flash.write(b"world")
```

Append data to the current file.

Parameters:

* `data`: `str` or `bytes`

Returns:

* number of bytes written

Notes:

* strings are automatically encoded to bytes
* large writes are automatically split into protocol-sized chunks
* raises `OSError` if the bridge reports a write error

### `write_line(text)`

```python
flash.write_line("temperature;humidity;pressure")
```

Append a line of text followed by `\n`.

Returns:

* number of bytes written

## Read operations

### `read_sector(sector)`

```python
data = flash.read_sector(0)
```

Read one raw 256-byte sector from flash.

Parameters:

* `sector`: sector number from `0` to `32767`

Returns:

* `bytes` object of length 256

This is useful for low-level inspection of flash content.

### `read(length=None)`

```python
content = flash.read()
content = flash.read(128)
```

Read file data from flash.

Parameters:

* `length`: optional maximum number of bytes to read

Returns:

* file content as `bytes`

Behavior:

* if `length` is `None`, the driver reads until the first `0xFF`
* if `length` is provided, it reads up to that many bytes

# Examples

| Example          | Description                                                            |
| ---------------- | ---------------------------------------------------------------------- |
| `flash_info.py`  | Display bridge ID, status, error register, busy flag, and filename     |
| `write_csv.py`   | Create a CSV file in flash, write a few lines, then read it back       |
| `read_file.py`   | Read and display the currently stored file                             |
| `erase_flash.py` | Erase the external flash memory                                       |
| `sensor_log.py`  | Log simulated sensor data to CSV, read it back, and compute statistics |
| `config_zone.py` | Test and demonstrate persistent config zone operations                 |

# Notes

* Flash file data is written to external memory through the DAPLink STM32F103 bridge.
* The config zone is managed separately by `DaplinkBridge` and survives `clear_flash()` operations.
* File naming follows the classic **8.3** format: up to 8 characters for the base name and 3 for the extension.
* For bridge-level operations (device ID, status, config zone), see the [`daplink_bridge`](../daplink_bridge/) documentation.

# Example mount command

```bash
mpremote mount lib run lib/daplink_flash/examples/flash_info.py
```
