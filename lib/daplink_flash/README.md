# DAPLink Flash MicroPython Driver

MicroPython driver for the **DAPLink Flash bridge** used on the STeaMi board.

This driver communicates over **I²C** with the STM32F103 DAPLink interface, which exposes access to an external **W25Q64JV SPI flash** and to a small persistent **config zone** stored in internal flash.

# Features

* I²C communication with the DAPLink flash bridge
* device identification with `WHO_AM_I`
* busy/status checking
* error reporting
* 8.3 filename management
* full flash erase
* append data to a file stored in flash
* line-based text writing helper
* sector-based raw flash reads
* full file readback
* persistent 1 KB config zone read/write
* config zone erase


# I²C Address

Default 7-bit I²C address: `0x3B`

# Basic Usage

```python
from machine import I2C
from daplink_flash import DaplinkFlash

i2c = I2C(1)
flash = DaplinkFlash(i2c)

print("WHO_AM_I:", hex(flash.device_id()))

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
flash = DaplinkFlash(i2c, address=0x3B)
```

Create a new DAPLink flash driver instance.

Parameters:

* `i2c`: initialized MicroPython `I2C` bus
* `address`: I²C address of the bridge, default is `0x3B`

## Device identification

### `device_id()`

```python
flash.device_id()
```

Read the `WHO_AM_I` register.

Expected value: `0x4C`

## Status

### `busy()`

```python
flash.busy()
```

Returns `True` if the flash bridge is currently busy, otherwise `False`.

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

This removes the stored file content.

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

## Config zone

The config zone is a **1 KB persistent storage area** located in the STM32F103 internal flash. It is separate from the external file storage and is suitable for keeping small persistent data such as calibration values, board revision, or other configuration data.  

### `clear_config()`

```python
flash.clear_config()
```

Erase the entire config zone.

Raises `OSError` if the operation fails.

### `write_config(data, offset=0)`

```python
flash.write_config("board_rev=3", offset=0)
flash.write_config(b"\x01\x02\x03", offset=100)
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
cfg = flash.read_config()
```

Read back config zone content.

Returns:

* `bytes` up to the first `0xFF`
* `b""` if the config zone is empty

# Examples

The repository provides the following example scripts:

| Example          | Description                                                                |
| ---------------- | -------------------------------------------------------------------------- |
| `flash_info.py`  | Display bridge ID, status, error register, busy flag, and current filename |
| `write_csv.py`   | Create a CSV file in flash, write a few lines, then read it back           |
| `read_file.py`   | Read and display the currently stored file                                 |
| `erase_flash.py` | Erase the external flash memory                                            |
| `sensor_log.py`  | Log simulated sensor data to CSV, read it back, and compute statistics     |
| `config_zone.py` | Test and demonstrate persistent config zone operations                     |

# Notes

* The bridge uses a `WHO_AM_I` value of `0x4C`. 
* Flash file data is written to external memory through the DAPLink STM32F103 bridge. 
* The config zone is separate from the external flash file area and survives `clear_flash()` operations. 
* File naming follows the classic **8.3** format: up to 8 characters for the base name and 3 for the extension.

# Example mount command

```bash
mpremote mount lib/daplink_flash run lib/daplink_flash/examples/flash_info.py
```
