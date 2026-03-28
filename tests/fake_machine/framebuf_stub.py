"""Stub for the MicroPython framebuf module."""

GS4_HMSB = 2


class FrameBuffer:
    """Minimal FrameBuffer stub for testing display drivers on CPython."""

    def __init__(self, buffer, width, height, fmt):
        self.buffer = buffer
        self.width = width
        self.height = height
        self.format = fmt

    def fill(self, col):
        val = (col & 0x0F) | ((col & 0x0F) << 4)
        for i in range(len(self.buffer)):
            self.buffer[i] = val

    def pixel(self, x, y, col=None):
        # GS4_HMSB: 2 pixels per byte, high nibble first
        idx = (y * self.width + x) // 2
        if col is None:
            byte = self.buffer[idx]
            return (byte >> 4) & 0x0F if x % 2 == 0 else byte & 0x0F
        byte = self.buffer[idx]
        if x % 2 == 0:
            self.buffer[idx] = ((col & 0x0F) << 4) | (byte & 0x0F)
        else:
            self.buffer[idx] = (byte & 0xF0) | (col & 0x0F)

    def text(self, string, x, y, col=15):
        pass

    def line(self, x1, y1, x2, y2, col):
        # Bresenham's line algorithm (simplified)
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        while True:
            self.pixel(x1, y1, col)
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

    def scroll(self, dx, dy):
        # Shift buffer content by (dx, dy) pixels
        buf_size = self.width * self.height // 2
        new_buf = bytearray(buf_size)
        for y in range(self.height):
            for x in range(self.width):
                src_x = x - dx
                src_y = y - dy
                if 0 <= src_x < self.width and 0 <= src_y < self.height:
                    col = self.pixel(src_x, src_y)
                    # Write to new buffer directly
                    idx = (y * self.width + x) // 2
                    byte = new_buf[idx]
                    if x % 2 == 0:
                        new_buf[idx] = (col << 4) | (byte & 0x0F)
                    else:
                        new_buf[idx] = (byte & 0xF0) | (col & 0x0F)
        self.buffer[:] = new_buf
