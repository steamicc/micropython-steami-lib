"""Register model of the MCP23009 interrupt logic, seen as an I2C bus.

It keeps the interrupt logic that matters for the D-pad, as the datasheet
(DS20002121C, 1.7.3 to 1.7.5) describes it: the first change on an enabled
pin sets INTF, copies the port into INTCAP and makes that port the compare
reference ("the default state is reset after an Interrupt occurs"). Later
changes, on any pin, raise no interrupt while INTF is set. Reading GPIO (or
INTCAP when IOCON.INTCC is set) clears it; if the port then differs from the
reference (a change made while INTF was set, still there), the interrupt
sets again at once with a new INTCAP (1.7.4, note). A change made and undone
while INTF was set leaves no trace. Shared by the mcp23009e driver tests and
the steami.Buttons tests.
"""

ADDR = 0x20

IODIR = 0x00
IPOL = 0x01
GPINTEN = 0x02
DEFVAL = 0x03
INTCON = 0x04
IOCON = 0x05
GPPU = 0x06
INTF = 0x07
INTCAP = 0x08
GPIO = 0x09
OLAT = 0x0A

# D-pad of the STeaMi V1c: active low, with pull-ups.
UP = 7
DOWN = 5
LEFT = 6
RIGHT = 4
DPAD = (UP, DOWN, LEFT, RIGHT)
RELEASED = 0xF0


class FakeMCP23009:
    """Register model of the MCP23009 interrupt logic, seen as an I2C bus.

    In "previous state" mode (INTCON bit clear), a pin is compared with a
    reference: the port value at the last interrupt, or at the last clear
    that found no interrupt set. With this model, enabling a pin that
    changed since then raises an interrupt at once: the spurious event seen
    on a V1c, when the reference is still the port before the pull-ups were
    set (0x00).

    Args:
        pins: input levels of the port.
        reference: compare reference (default: pins).
    """

    def __init__(self, pins=RELEASED, reference=None):
        self.regs = [0] * 11
        self.regs[IODIR] = 0xFF
        self.pins = pins
        self.reference = pins if reference is None else reference
        self.log = []
        # Called as on_write(reg, value) once a write is applied, and as
        # on_read(reg) once a read is applied, to run code where a
        # scheduled IRQ could run on the board.
        self.on_write = None
        self.on_read = None

    # ----- Chip side -----

    def press(self, gp):
        self.pins &= ~(1 << gp)
        self._update()

    def release(self, gp):
        self.pins |= 1 << gp
        self._update()

    def _update(self):
        if self.regs[INTF]:
            return
        intcon = self.regs[INTCON]
        changed = ((self.pins ^ self.reference) & ~intcon) | (
            (self.pins ^ self.regs[DEFVAL]) & intcon
        )
        changed &= self.regs[GPINTEN]
        if changed:
            self.regs[INTF] = changed
            self.regs[INTCAP] = self.pins
            self.reference = self.pins

    def _clear(self):
        # A change made while INTF was set, and still there, sets the
        # interrupt again. With no interrupt set, the reference follows the port.
        if not self.regs[INTF]:
            self.reference = self.pins
        self.regs[INTF] = 0
        self._update()

    # ----- I2C side -----

    def readfrom_mem(self, addr, reg, nbytes, *, addrsize=8):
        assert addr == ADDR
        self.log.append(("r", reg))
        value = self.pins if reg == GPIO else self.regs[reg]
        clearing = INTCAP if self.regs[IOCON] & 0x01 else GPIO
        if reg == clearing:
            self._clear()
        if self.on_read is not None:
            self.on_read(reg)
        return bytes([value])

    def writeto_mem(self, addr, reg, buf, *, addrsize=8):
        assert addr == ADDR
        self.log.append(("w", reg))
        self.regs[reg] = buf[0]
        self._update()
        if self.on_write is not None:
            self.on_write(reg, buf[0])
