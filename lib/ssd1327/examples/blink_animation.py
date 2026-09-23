"""Blink animation example using framebuf blit and pixel scaling on SSD1327 OLED.

Displays a scaled 16x16 eye bitmap centered on the 128x128 round OLED screen
and animates a smooth blink sequence by cycling through five eye states.

Demonstrates:
    - framebuf.FrameBuffer creation from raw bitmap data (MONO_HLSB)
    - Pixel-by-pixel scaling using fill_rect
    - framebuf.blit() to copy a scaled bitmap onto the display framebuffer
    - Frame-based animation with variable timing per frame
"""

from time import sleep_ms

import framebuf
import micropython
import ssd1327
from machine import SPI, Pin

# === Display setup ===
spi = SPI(1)
dc = Pin("DATA_COMMAND_DISPLAY")
res = Pin("RST_DISPLAY")
cs = Pin("CS_DISPLAY")
display = ssd1327.WS_OLED_128X128_SPI(spi, dc, res, cs)

# === Bitmap dimensions and scale ===
EYE_W = 16
EYE_H = 16
SCALE = 6  # Each pixel becomes a 6x6 block → 96x96px on screen

# === Eye bitmaps (MONO_HLSB, 16x16, 2 bytes per row) ===

EYE_OPEN = bytearray(
    [
        0b00000000,
        0b00000000,
        0b00111111,
        0b10000000,
        0b01000000,
        0b01000000,
        0b10011001,
        0b10010000,
        0b10100101,
        0b01010000,
        0b10000001,
        0b10000000,
        0b01000000,
        0b01000000,
        0b00111111,
        0b10000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
    ]
)

EYE_SQUINT = bytearray(
    [
        0b00000000,
        0b00000000,
        0b00111111,
        0b10000000,
        0b01000000,
        0b01000000,
        0b10011001,
        0b10010000,
        0b10011001,
        0b10010000,
        0b10000001,
        0b10000000,
        0b01000000,
        0b01000000,
        0b00111111,
        0b10000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
    ]
)

EYE_HALF = bytearray(
    [
        0b00000000,
        0b00000000,
        0b00111111,
        0b10000000,
        0b01000000,
        0b01000000,
        0b10000001,
        0b10010000,
        0b10111101,
        0b01010000,
        0b10000001,
        0b10000000,
        0b01000000,
        0b01000000,
        0b00111111,
        0b10000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
    ]
)

EYE_CLOSED = bytearray(
    [
        0b00000000,
        0b00000000,
        0b00111111,
        0b10000000,
        0b01000000,
        0b01000000,
        0b10000000,
        0b00010000,
        0b10111111,
        0b11010000,
        0b10000000,
        0b00000000,
        0b01000000,
        0b01000000,
        0b00111111,
        0b10000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
        0b00000000,
    ]
)

# === Animation: open → squint → half → closed → half → squint → open ===
BLINK_FRAMES = [
    EYE_OPEN,
    EYE_SQUINT,
    EYE_HALF,
    EYE_CLOSED,
    EYE_CLOSED,
    EYE_HALF,
    EYE_SQUINT,
    EYE_OPEN,
]

FRAME_DELAYS = [1200, 60, 50, 40, 40, 50, 60, 400]  # ms per frame


@micropython.native
def draw_eye(bitmap):
    """Draw a scaled eye bitmap centered on the 128x128 display."""
    buf = framebuf.FrameBuffer(bitmap, EYE_W, EYE_H, framebuf.MONO_HLSB)

    scaled_w = EYE_W * SCALE
    scaled_h = EYE_H * SCALE
    scaled_bitmap = bytearray((scaled_w * scaled_h) // 8)
    scaled_buf = framebuf.FrameBuffer(
        scaled_bitmap, scaled_w, scaled_h, framebuf.MONO_HLSB
    )

    # Scale up pixel by pixel
    for y in range(EYE_H):
        for x in range(EYE_W):
            if buf.pixel(x, y):
                scaled_buf.fill_rect(x * SCALE, y * SCALE, SCALE, SCALE, 1)

    x_offset = (128 - scaled_w) // 2
    y_offset = (128 - scaled_h) // 2
    display.fill(0)
    display.framebuf.blit(scaled_buf, x_offset, y_offset)
    display.show()


# === Animation loop ===
try:
    while True:
        for frame, delay in zip(BLINK_FRAMES, FRAME_DELAYS):
            draw_eye(frame)
            sleep_ms(delay)
except KeyboardInterrupt:
    pass
finally:
    display.fill(0)
    display.show()
