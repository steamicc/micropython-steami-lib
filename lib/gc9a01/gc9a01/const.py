from micropython import const

# panel geometry
WIDTH = const(240)
HEIGHT = const(240)

# standard commands (MIPI DCS)
SWRESET = const(0x01)
SLPIN = const(0x10)
SLPOUT = const(0x11)
DISPOFF = const(0x28)
DISPON = const(0x29)
CASET = const(0x2A)
RASET = const(0x2B)
RAMWR = const(0x2C)

# SPI mode 0 at 32 MHz, the SPI1 maximum on the STeaMi (64 MHz PCLK2 / 2):
# a 7 680-byte strip takes 2.0 ms instead of 3.9 ms at 16 MHz. If the panel
# does not hold 32 MHz, set 16_000_000 here (the earlier, proven speed).
BAUDRATE = const(32_000_000)

# rows converted to RGB565 per SPI write in show(): 16 rows of 240 pixels
# take 7680 bytes, well below the 65535-byte DMA limit
STRIP_ROWS = const(16)

# delays (milliseconds)
RESET_PULSE_MS = const(10)
RESET_DELAY_MS = const(120)
SLEEP_DELAY_MS = const(120)
DISPON_DELAY_MS = const(20)

# Initialisation sequence: command, parameter count, parameters.
# kInitSequence of the Arduino SteamiGC9A01.cpp (GC9A01 manufacturer
# sequence; 0xFE and 0xEF unlock the extended registers), then MADCTL for
# the V1c orientation and INVON (the V1c IPS panel needs the inversion on).
INIT_SEQUENCE = (
    b"\xef\x00"
    b"\xeb\x01\x14"
    b"\xfe\x00"
    b"\xef\x00"
    b"\xeb\x01\x14"
    b"\x84\x01\x40"
    b"\x85\x01\xff"
    b"\x86\x01\xff"
    b"\x87\x01\xff"
    b"\x88\x01\x0a"
    b"\x89\x01\x21"
    b"\x8a\x01\x00"
    b"\x8b\x01\x80"
    b"\x8c\x01\x01"
    b"\x8d\x01\x01"
    b"\x8e\x01\xff"
    b"\x8f\x01\xff"
    b"\xb6\x02\x00\x20"  # display function control: SS, V1c orientation
    b"\x3a\x01\x05"  # COLMOD: RGB565
    b"\x90\x04\x08\x08\x08\x08"
    b"\xbd\x01\x06"
    b"\xbc\x01\x00"
    b"\xff\x03\x60\x01\x04"
    b"\xc3\x01\x13"  # power control 2
    b"\xc4\x01\x13"  # power control 3
    b"\xc9\x01\x22"  # power control 4
    b"\xbe\x01\x11"
    b"\xe1\x02\x10\x0e"
    b"\xdf\x03\x21\x0c\x02"
    b"\xf0\x06\x45\x09\x08\x08\x26\x2a"  # gamma 1
    b"\xf1\x06\x43\x70\x72\x36\x37\x6f"  # gamma 2
    b"\xf2\x06\x45\x09\x08\x08\x26\x2a"  # gamma 3
    b"\xf3\x06\x43\x70\x72\x36\x37\x6f"  # gamma 4
    b"\xed\x02\x1b\x0b"
    b"\xae\x01\x77"
    b"\xcd\x01\x63"
    b"\x70\x09\x07\x07\x04\x0e\x0f\x09\x07\x08\x03"
    b"\xe8\x01\x34"  # frame rate
    b"\x62\x0c\x18\x0d\x71\xed\x70\x70\x18\x0f\x71\xef\x70\x70"
    b"\x63\x0c\x18\x11\x71\xf1\x70\x70\x18\x13\x71\xf3\x70\x70"
    b"\x64\x07\x28\x29\xf1\x01\xf1\x00\x07"
    b"\x66\x0a\x3c\x00\xcd\x67\x45\x45\x10\x00\x00\x00"
    b"\x67\x0a\x00\x3c\x00\x00\x00\x01\x54\x10\x32\x98"
    b"\x74\x07\x10\x85\x80\x00\x00\x4e\x00"
    b"\x98\x02\x3e\x07"
    b"\x36\x01\x08"  # MADCTL: BGR, V1c orientation
    b"\x21\x00"  # INVON
)

# The 16 colours of the frame (index: RGB).
PALETTE = (
    (0, 0, 0),  # 0 BLACK
    (51, 51, 51),  # 1 GRID_DARK
    (102, 102, 102),  # 2 DARK
    (153, 153, 153),  # 3 GRAY
    (187, 187, 187),  # 4 LIGHT
    (255, 255, 255),  # 5 WHITE
    (119, 255, 119),  # 6 GREEN
    (255, 85, 85),  # 7 RED
    (85, 85, 255),  # 8 BLUE
    (255, 255, 85),  # 9 YELLOW
    (85, 255, 255),  # 10 CYAN
    (255, 85, 255),  # 11 MAGENTA
    (255, 165, 0),  # 12 ORANGE
    (0, 128, 0),  # 13 DARK_GREEN
    (128, 0, 0),  # 14 DARK_RED
    (0, 0, 128),  # 15 DARK_BLUE
)

# PALETTE in RGB565, byte-swapped: framebuf stores words little-endian, so
# these words land in memory high byte first, the order the panel reads.
PALETTE_RGB565 = (
    0x0000,  # 0x0000
    0x8631,  # 0x3186
    0x2C63,  # 0x632C
    0xD39C,  # 0x9CD3
    0xD7BD,  # 0xBDD7
    0xFFFF,  # 0xFFFF
    0xEE77,  # 0x77EE
    0xAAFA,  # 0xFAAA
    0xBF52,  # 0x52BF
    0xEAFF,  # 0xFFEA
    0xFF57,  # 0x57FF
    0xBFFA,  # 0xFABF
    0x20FD,  # 0xFD20
    0x0004,  # 0x0400
    0x0080,  # 0x8000
    0x1000,  # 0x0010
)
