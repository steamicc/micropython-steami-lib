# MicroPython library for MCP23009E I/O Expander

This library provides a complete driver to control the MCP23009E I/O expander on the STeaMi board.

## Features

- **Full GPIO control**: Configure pins as input/output, read/write levels
- **Pull-up resistors**: Built-in pull-up support
- **Interrupt support**: Hardware interrupts with callback system
- **Pin-compatible API**: `MCP23009Pin` class compatible with `machine.Pin`
- **Register access**: Low-level register access for advanced usage

## I²C Address

The base I²C address is \`0x20\` (A0=A1=A2=LOW). On the STeaMi board, the address is \`0x20\`.

## Quick Start

### Basic Usage with MCP23009E class

```python
from machine import I2C, Pin
from mcp23009e import MCP23009E
from mcp23009e.const import *

# Initialize I2C and reset pin
bus = I2C(1)
reset = Pin("RST_EXPANDER", Pin.OUT)

# Create driver instance
mcp = MCP23009E(bus, address=MCP23009_I2C_ADDR, reset_pin=reset)

# Configure a GPIO as input with pull-up
mcp.setup(7, MCP23009_DIR_INPUT, pullup=MCP23009_PULLUP)

# Read the level
level = mcp.get_level(7)
print(f"GPIO 7 level: {level}")

# Configure a GPIO as output
mcp.setup(0, MCP23009_DIR_OUTPUT)
mcp.set_level(0, MCP23009_LOGIC_HIGH)
```

### Pin-Compatible API with MCP23009Pin

The `MCP23009Pin` class provides a **machine.Pin-compatible** interface:

```python
from machine import I2C, Pin
from mcp23009e import MCP23009E, MCP23009Pin
from mcp23009e.const import *

# Initialize
bus = I2C(1)
reset = Pin("RST_EXPANDER", Pin.OUT)
mcp = MCP23009E(bus, address=MCP23009_I2C_ADDR, reset_pin=reset)

# Create a Pin object for a button
btn = MCP23009Pin(mcp, 7, MCP23009Pin.IN, MCP23009Pin.PULL_UP)
print(f"Button state: {btn.value()}")

# Create a Pin object for a LED
led = MCP23009Pin(mcp, 0, MCP23009Pin.OUT)
led.on()   # Turn on
led.off()  # Turn off
led.toggle()  # Toggle state
```

### Interrupts

```python
from machine import I2C, Pin
from mcp23009e import MCP23009E, MCP23009Pin
from mcp23009e.const import *

# Initialize with interrupt pin
bus = I2C(1)
reset = Pin("RST_EXPANDER", Pin.OUT)
interrupt = Pin("INT_EXPANDER", Pin.IN)
mcp = MCP23009E(bus, address=MCP23009_I2C_ADDR, reset_pin=reset, interrupt_pin=interrupt)

# Create pin and configure interrupt
btn = MCP23009Pin(mcp, 7, MCP23009Pin.IN, MCP23009Pin.PULL_UP)

def callback(pin):
    print(f"Button state changed: {pin.value()}")

btn.irq(handler=callback, trigger=MCP23009Pin.IRQ_FALLING | MCP23009Pin.IRQ_RISING)
```

## API Reference

### MCP23009E Class

#### Constructor

```python
MCP23009E(i2c, address, reset_pin, interrupt_pin=None)
```

#### Main Methods

* `setup(gpx, direction, pullup, polarity)` - Configure a GPIO
* `set_level(gpx, level)` - Set output level
* `get_level(gpx)` - Read input level
* `interrupt_on_change(gpx, callback)` - Register change callback
* `interrupt_on_falling(gpx, callback)` - Register falling edge callback
* `interrupt_on_raising(gpx, callback)` - Register rising edge callback
* `disable_interrupt(gpx)` - Disable interrupts on a GPIO

### MCP23009Pin Class

#### Constructor

```python
MCP23009Pin(mcp, pin_number, mode=-1, pull=-1, value=None)
```

#### Methods (machine.Pin compatible)

* `init(mode, pull, value)` - (Re)configure the pin
* `value(x=None)` - Get or set pin value
* `on()` - Set pin high
* `off()` - Set pin low
* `toggle()` - Toggle pin state
* `irq(handler, trigger)` - Configure interrupt
* `mode(mode=None)` - Get or set mode
* `pull(pull=None)` - Get or set pull configuration

#### Constants

* `MCP23009Pin.IN` / `MCP23009Pin.OUT` - Pin modes
* `MCP23009Pin.PULL_UP` - Pull-up configuration
* `MCP23009Pin.IRQ_FALLING` / `MCP23009Pin.IRQ_RISING` - Interrupt triggers

### MCP23009ActiveLowPin Class

Special pin class for **active-low configurations** (LEDs connected between VCC and GPIO).

The MCP23009E can sink more current (25mA) than it can source (~1mA). For LEDs and similar loads, use this configuration:

```
3.3V → [LED] → [Resistor 220-330Ω] → GPIO
```

With `MCP23009ActiveLowPin`, the logic is automatically inverted:

* `led.on()` → GPIO LOW → LED lights up
* `led.off()` → GPIO HIGH → LED turns off

#### Example

```python
from mcp23009e import MCP23009E, MCP23009ActiveLowPin

mcp = MCP23009E(bus, address=MCP23009_I2C_ADDR, reset_pin=reset)

# Create an active-low LED
led = MCP23009ActiveLowPin(mcp, 0)
led.on()   # LED lights up (GPIO goes LOW)
led.off()  # LED turns off (GPIO goes HIGH)
led.toggle()  # Toggle LED state
```

The API is identical to `MCP23009Pin` - just use `MCP23009ActiveLowPin` instead.

## Power Management

The driver provides simple hardware power management helpers through the reset pin:

### Power off

```python
mcp.power_off()
```

Holds the reset pin low.

### Power on

```python
mcp.power_on()
```

Releases the reset pin.

### Reset

```python
mcp.reset()
```
Toggles the reset pin to perform a hardware reset.

## Examples

The library includes several examples:

* `buttons.py` - Simple button reading with polling
* `i2c_scan.py` - Scan I2C buses for connected devices
* `test_basic.py` - Basic driver functionality tests
* `test_interrupts.py` - Interrupt system demonstration
* `test_led_simple.py` - Basic active-low LED control example
* `test_output_active_low.py` - Active-low output tests with inverted logic
* `test_output.py` - GPIO output tests using low-level and Pin APIs
* `test_pin.py` - MCP23009Pin class usage examples
* `test_pin_irq.py` - Pin-compatible interrupt examples


### How to run 

```python
mpremote mount lib/mcp23009e run lib/mcp23009e/examples/test_basic.py
```